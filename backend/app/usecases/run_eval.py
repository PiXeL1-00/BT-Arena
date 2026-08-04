"""Run evaluation usecase -- orchestrate debate + scoring for a single case."""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Final, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.schemas import (
    CaseStatus,
    EventType,
    JudgeDecision,
    RunStatus,
    ScoringMode,
    VerdictEnum,
)
from app.core.domain.scoring import compute_case_score
from app.infra.db.repository import Repository
from app.infra.debate.runner import DebateController
from app.infra.debate.schemas import FALLBACK_JUDGE_REASONING, MessageEvent, PhaseEvent
from app.infra.llm.factory import get_llm_client
from app.config import settings
from app.infra.sse.event_bus import EventBus, emit_and_persist
from app.core.domain.exceptions import QuotaExhaustedError

logger = logging.getLogger(__name__)

QUOTA_EXHAUSTED_MESSAGES: Final[tuple[str, ...]] = (
    "🪭 {provider} ran out of juice! Quota's tapped out — the meter hit zero. "
    "Time to upgrade or wait for a refill.",
    "🚫 {provider} just pulled the velvet rope. Daily quota exceeded — "
    "even AIs need a budget. Try again tomorrow or upgrade your plan.",
    "⛽ {provider} is running on empty. You've burned through today's free-tier tokens. "
    "Top up or wait for the midnight reset.",
    "🎰 {provider} says: 'No more spins today!' You've hit the daily request limit. "
    "Upgrade for unlimited plays.",
    "🧊 {provider} put your requests on ice. Quota frozen until reset. "
    "Warm it up with a billing upgrade or wait it out.",
)


class RunEvalUsecase:

    def __init__(self, session: AsyncSession, event_bus: EventBus) -> None:
        self._session = session
        self._repo = Repository(session)
        self._bus = event_bus
        self._db_lock = asyncio.Lock()

    async def execute(
        self, *,
        dataset_id: str,
        case_id: str,
        models: list[dict[str, str]],
        run_id: Optional[str] = None,
    ) -> str:
        if run_id is None:
            run_id = str(uuid.uuid4())

        models_json = [{"provider": m["provider"], "model_name": m["model_name"]} for m in models]

        # Record scoring mode for auditability / run comparison
        scoring_mode = ScoringMode.ML.value if settings.ml_scoring_enabled else ScoringMode.DETERMINISTIC.value

        existing = await self._repo.get_run(run_id)
        if existing is None:
            await self._repo.create_run(
                run_id=run_id,
                dataset_id=dataset_id,
                case_id=case_id,
                models_json=models_json,
                scoring_mode=scoring_mode,
            )

        await self._repo.update_run_status(run_id, status=RunStatus.RUNNING)
        await self._repo.commit()

        await self._emit(run_id, EventType.RUN_STARTED, {
            "run_id": run_id, "dataset_id": dataset_id, "models": models_json,
        })

        try:
            case_row = await self._repo.get_dataset_case(dataset_id, case_id)
            if case_row is None:
                raise ValueError(f"Case {case_id} not found in dataset {dataset_id}")

            await self._emit(run_id, EventType.CASE_STARTED, {
                "case_id": case_row.case_id,
                "case_index": 0,
                "total_cases": 1,
                "topic": case_row.topic,
                "claim": case_row.claim,
                "pressure_score": case_row.pressure_score,
            })

            exhausted_providers: set[str] = set()
            for model_cfg in models:
                model_key = f"{model_cfg['provider']}/{model_cfg['model_name']}"
                if model_cfg["provider"] in exhausted_providers:
                    logger.info(
                        "Skipping %s — provider %s quota exhausted",
                        model_key, model_cfg["provider"],
                    )
                    continue
                try:
                    await self._run_case(
                        run_id=run_id, case_row=case_row,
                        model_cfg=model_cfg, model_key=model_key,
                    )
                except QuotaExhaustedError as qe:
                    exhausted_providers.add(qe.provider)

            await self._emit(run_id, EventType.METRICS_UPDATE, {
                "completed": 1, "total": 1,
            })

            await self._repo.update_run_status(
                run_id, status=RunStatus.COMPLETED, finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            await self._repo.commit()

            # register cache slot if enabled (single-model only)
            if settings.store_result and len(models) == 1:
                mk = f"{models[0]['provider']}/{models[0]['model_name']}"
                slot_num = await self._repo.get_next_empty_slot_number(
                    dataset_id, mk, case_id, max_slots=settings.cache_results,
                )
                if slot_num is not None:
                    await self._repo.create_cache_slot(
                        dataset_id=dataset_id, model_key=mk,
                        case_id=case_id, slot_number=slot_num,
                        source_run_id=run_id,
                    )
                    await self._repo.commit()

            await self._emit(run_id, EventType.RUN_FINISHED, {"run_id": run_id})

        except Exception as exc:
            logger.exception("Run %s failed", run_id)
            try:
                await self._safe_rollback(run_id)
                await self._repo.update_run_status(
                    run_id, status=RunStatus.FAILED, finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                await self._repo.commit()
            except Exception:
                logger.warning("failed to set run %s to FAILED status", run_id)
            await self._emit(run_id, EventType.RUN_FINISHED, {
                "run_id": run_id, "error": str(exc),
            })

        return run_id

    async def _run_case(
        self, *, run_id: str, case_row: Any,
        model_cfg: dict[str, str], model_key: str,
    ) -> None:
        await self._repo.upsert_case_status(
            run_id=run_id, case_id=case_row.case_id,
            model_key=model_key, status=CaseStatus.RUNNING,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        await self._repo.commit()

        try:
            llm = get_llm_client(
                provider=model_cfg["provider"],
                model_name=model_cfg["model_name"],
                api_key_override=model_cfg.get("api_key_override"),
            )

            if settings.use_autogen_debate:
                from app.infra.llm.autogen_model_client import GalileoModelClient
                from app.infra.debate.autogen_debate_flow import AutoGenDebateController

                autogen_client = GalileoModelClient(
                    llm,
                    model_name=model_cfg["model_name"],
                    provider=model_cfg["provider"],
                    enable_function_calling=settings.autogen_enable_tools,
                )
                controller = AutoGenDebateController(
                    autogen_client, model_key,
                    max_cross_exam_messages=settings.autogen_max_cross_exam_messages,
                    enable_tools=settings.autogen_enable_tools,
                )
            else:
                controller = DebateController(llm, model_key)

            async def on_msg(evt: MessageEvent) -> None:
                async with self._db_lock:
                    await self._repo.add_message(
                        run_id=run_id, case_id=evt.case_id,
                        model_key=model_key, role=evt.role,
                        content=evt.content, phase=evt.phase, round=evt.round,
                    )
                    await self._repo.commit()
                    await self._emit(run_id, EventType.AGENT_MESSAGE, {
                        "case_id": evt.case_id, "model_key": model_key,
                        "role": evt.role, "phase": evt.phase,
                        "round": evt.round, "content": evt.content[:2000],
                    })

            async def on_phase(evt: PhaseEvent) -> None:
                await self._emit(run_id, EventType.CASE_PHASE_STARTED, {
                    "case_id": evt.case_id, "model_key": model_key, "phase": evt.phase,
                })

            # LABEL ISOLATION: only case_id, claim, topic, and evidence are
            # passed to the debate controller.  Ground-truth label and
            # safe_to_answer are used ONLY at scoring time below.
            debate = await controller.run(
                case_id=case_row.case_id,
                claim=case_row.claim,
                topic=case_row.topic,
                evidence_packets=case_row.evidence_json,
                on_message=on_msg,
                on_phase=on_phase,
            )

            valid_eids = {ep["eid"] for ep in case_row.evidence_json}
            try:
                judge_decision = JudgeDecision(**debate.judge_json)
            except Exception:
                judge_decision = JudgeDecision(
                    verdict=VerdictEnum.INSUFFICIENT, confidence=0.0,
                    evidence_used=[], reasoning=FALLBACK_JUDGE_REASONING,
                )

            # NOTE: label is only used at scoring time -- the debate controller
            # never sees it, preserving label isolation.
            safe_flag: bool = getattr(case_row, "safe_to_answer", True)

            # --- ML scoring (optional, non-blocking) ---
            ml_scores = None
            if settings.ml_scoring_enabled:
                from app.infra.ml.scorer import compute_ml_scores_async

                evidence_map = {
                    ep["eid"]: ep["summary"] for ep in case_row.evidence_json
                }
                ml_scores = await compute_ml_scores_async(
                    judge_decision.reasoning,
                    judge_decision.evidence_used,
                    evidence_map,
                )

            breakdown = compute_case_score(
                judge_decision,
                label=VerdictEnum(case_row.label),
                valid_eids=valid_eids,
                safe_to_answer=safe_flag if isinstance(safe_flag, bool) else True,
                ml_scores=ml_scores,
            )

            # Persist ML diagnostics in the existing judge_json column
            judge_json_out: dict[str, Any] = dict(debate.judge_json) if debate.judge_json else {}
            judge_json_out["score_breakdown"] = {
                "correctness": breakdown.correctness,
                "grounding": breakdown.grounding,
                "calibration": breakdown.calibration,
                "falsifiable": breakdown.falsifiable,
                "deference_penalty": breakdown.deference_penalty,
                "refusal_penalty": breakdown.refusal_penalty,
            }
            if ml_scores is not None:
                judge_json_out["ml_scores"] = asdict(ml_scores)
                judge_json_out["scoring_mode"] = ScoringMode.ML.value
            else:
                judge_json_out["scoring_mode"] = ScoringMode.DETERMINISTIC.value

            await self._repo.add_result(
                run_id=run_id, case_id=case_row.case_id, model_key=model_key,
                verdict=judge_decision.verdict.value, label=case_row.label,
                passed=breakdown.passed, score=breakdown.total,
                confidence=judge_decision.confidence,
                evidence_used_json=judge_decision.evidence_used,
                critical_fail_reason=breakdown.critical_fail_reason,
                latency_ms=debate.total_latency_ms,
                cost_estimate=debate.total_cost,
                judge_json=judge_json_out,
            )
            await self._repo.commit()

            # best-effort: bridge to analytics ledger
            await self._bridge_result(
                run_id=run_id, case_id=case_row.case_id, model_key=model_key,
            )

            await self._emit(run_id, EventType.CASE_SCORED, {
                "case_id": case_row.case_id, "model_key": model_key,
                "score": breakdown.total, "passed": breakdown.passed,
                "verdict": judge_decision.verdict.value,
            })

        except QuotaExhaustedError as qe:
            user_msg = random.choice(QUOTA_EXHAUSTED_MESSAGES).format(provider=qe.provider.capitalize())
            logger.warning("Quota exhausted for %s on case %s: %s", model_key, case_row.case_id, qe)
            try:
                await self._safe_rollback(run_id)
                await self._repo.add_result(
                    run_id=run_id, case_id=case_row.case_id, model_key=model_key,
                    verdict=VerdictEnum.INSUFFICIENT.value, label=case_row.label,
                    passed=False, score=0, confidence=0.0,
                    evidence_used_json=[], critical_fail_reason=user_msg,
                    latency_ms=0, cost_estimate=0.0, judge_json={},
                )
                await self._repo.commit()
            except Exception:
                logger.warning("failed to persist quota-exhausted result for case %s model %s", case_row.case_id, model_key)
            await self._emit(run_id, EventType.QUOTA_EXHAUSTED, {
                "model_key": model_key, "provider": qe.provider, "message": user_msg,
            })
            raise

        except Exception as exc:
            logger.error("case %s model %s blew up: %s", case_row.case_id, model_key, exc)
            try:
                await self._safe_rollback(run_id)
                await self._repo.add_result(
                    run_id=run_id, case_id=case_row.case_id, model_key=model_key,
                    verdict=VerdictEnum.INSUFFICIENT.value, label=case_row.label,
                    passed=False, score=0, confidence=0.0,
                    evidence_used_json=[], critical_fail_reason=str(exc),
                    latency_ms=0, cost_estimate=0.0, judge_json={},
                )
                await self._repo.commit()
            except Exception:
                logger.warning("failed to persist error result for case %s model %s", case_row.case_id, model_key)

        finally:
            try:
                await self._safe_rollback(run_id)
                await self._repo.upsert_case_status(
                    run_id=run_id, case_id=case_row.case_id,
                    model_key=model_key, status=CaseStatus.COMPLETED,
                    finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                await self._repo.commit()
            except Exception:
                logger.warning("failed to persist case completion for case %s model %s", case_row.case_id, model_key)

    async def _safe_rollback(self, run_id: str) -> None:
        try:
            await self._session.rollback()
        except Exception:
            logger.warning("rollback failed (session corrupted): run_id=%s", run_id)

    async def _emit(self, run_id: str, event_type: str, payload: dict) -> None:
        await emit_and_persist(self._bus, self._repo, run_id, event_type, payload)

    async def _bridge_result(
        self, *, run_id: str, case_id: str, model_key: str,
    ) -> None:
        results = await self._repo.get_run_results(
            run_id, model_key=model_key, case_id=case_id,
        )
        if not results:
            return
        run = await self._repo.get_run(run_id)
        if not run:
            return
        from app.usecases.analytics_bridge import bridge_run_result_to_eval
        await bridge_run_result_to_eval(self._session, results[-1], run)
