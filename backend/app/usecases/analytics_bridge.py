"""Best-effort bridge: RunResultRow → GalileoEvalRunRow.

Uses a nested savepoint so failures never roll back the core pipeline.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.model_identity import parse_model_key
from app.core.domain.schemas import EvalMode, RunType
from app.infra.db.galileo_repository import GalileoRepository
from app.infra.db.models import GalileoEvalRunRow, RunResultRow, RunRow

logger = logging.getLogger(__name__)


async def bridge_run_result_to_eval(
    session: AsyncSession,
    result: RunResultRow,
    run: RunRow,
    *,
    run_type: str = RunType.USER.value,
    batch_id: Optional[str] = None,
    eval_mode: str = EvalMode.GALILEO.value,
) -> None:
    """Map a RunResultRow into the analytics ledger. Best-effort."""
    try:
        async with session.begin_nested():
            identity = parse_model_key(result.model_key)
            repo = GalileoRepository(session)
            llm = await repo.find_or_create_llm(
                provider=identity.provider,
                model_name=identity.model_name,
                model_version=identity.version,
            )

            score_components = _extract_score_components(result)

            row = GalileoEvalRunRow(
                llm_id=llm.id,
                dataset_id=run.dataset_id,
                case_id=run.case_id,
                eval_mode=eval_mode,
                score_total=Decimal(str(result.score)),
                score_components=score_components,
                failure_flags=_extract_failure_flags(result),
                run_type=run_type,
                batch_id=batch_id,
                source_run_id=run.run_id,
                latency_ms=result.latency_ms,
                cost_usd=Decimal(str(result.cost_estimate)) if result.cost_estimate else None,
            )
            session.add(row)
    except Exception:
        logger.warning(
            "Analytics bridge failed for run=%s model=%s, continuing",
            run.run_id, result.model_key,
            exc_info=True,
        )


def _extract_score_components(result: RunResultRow) -> dict | None:
    judge = result.judge_json
    if not judge:
        return None
    breakdown = judge.get("score_breakdown")
    if isinstance(breakdown, dict):
        return breakdown
    return None


def _extract_failure_flags(result: RunResultRow) -> dict | None:
    flags: dict[str, object] = {}
    if result.critical_fail_reason:
        flags["critical_fail"] = result.critical_fail_reason
    if not result.passed:
        flags["not_passed"] = True
    if result.verdict and result.label and result.verdict != result.label:
        flags["wrong_verdict"] = f"{result.verdict}→{result.label}"
    if result.score is not None and result.score < 40:
        flags["low_score"] = True
    return flags or None
