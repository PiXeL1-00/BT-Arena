"""Replay a cached result set -- re-emit stored events with proportional delays."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.schemas import CaseStatus, EventType, RunStatus
from app.infra.db.models import RunEventRow, RunMessageRow, RunResultRow
from app.infra.db.repository import Repository
from app.infra.sse.event_bus import EventBus, emit_and_persist

logger = logging.getLogger(__name__)

INITIAL_DELAY_SECONDS = 2.0
MAX_REPLAY_SECONDS = 45.0
MIN_EVENT_DELAY = 0.03
MAX_EVENT_DELAY = 2.0


def _msg_key(
    case_id: str, model_key: str, role: str,
    phase: Optional[str], round_num: Optional[int],
) -> tuple:
    return (case_id, model_key, role, phase, round_num)


def _result_key(case_id: str, model_key: str) -> tuple:
    return (case_id, model_key)


class ReplayCachedUsecase:

    def __init__(
        self, session: AsyncSession, event_bus: EventBus,
        *, run_id: str, source_run_id: str,
    ) -> None:
        self._repo = Repository(session)
        self._bus = event_bus
        self._run_id = run_id
        self._source_run_id = source_run_id

    async def execute(self) -> None:
        try:
            await self._do_replay()
        except Exception:
            logger.exception("Replay failed: run_id=%s source=%s", self._run_id, self._source_run_id)
            await self._fail("unexpected error during replay")

    async def _do_replay(self) -> None:
        # 1. Validate source run
        source = await self._repo.get_run(self._source_run_id)
        if source is None or source.status != RunStatus.COMPLETED:
            await self._fail("Source run invalid or not completed")
            return

        events = await self._repo.get_all_run_events(self._source_run_id)
        if not events:
            await self._fail("Source run has no events")
            return

        # 2. Wait for frontend to subscribe to SSE
        await asyncio.sleep(INITIAL_DELAY_SECONDS)

        # 3. Build lookup dicts from source data
        msg_map = await self._build_message_map()
        result_map = await self._build_result_map()

        # 4. Compute proportional timing
        delays = _compute_delays(events)

        # 5. Set run to RUNNING
        await self._repo.update_run_status(self._run_id, status=RunStatus.RUNNING)
        await self._repo.commit()

        # 6. Iterate events
        for idx, evt in enumerate(events):
            if idx > 0:
                await asyncio.sleep(delays[idx])
            await self._replay_event(evt, msg_map, result_map)

        # 7. Mark completed
        await self._repo.update_run_status(
            self._run_id, status=RunStatus.COMPLETED, finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        await self._repo.commit()

    async def _replay_event(
        self, evt: RunEventRow,
        msg_map: dict[tuple, RunMessageRow],
        result_map: dict[tuple, RunResultRow],
    ) -> None:
        etype = evt.event_type
        payload: dict = dict(evt.payload_json)

        if etype in (EventType.RUN_STARTED, EventType.RUN_FINISHED):
            payload["run_id"] = self._run_id
            await self._emit(etype, payload)

        elif etype == EventType.CASE_STARTED:
            model_key = payload.get("model_key")
            case_id = payload.get("case_id", "")
            if model_key:
                await self._repo.upsert_case_status(
                    run_id=self._run_id, case_id=case_id,
                    model_key=model_key, status=CaseStatus.RUNNING,
                    started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                await self._repo.commit()
            await self._emit(etype, payload)

        elif etype == EventType.AGENT_MESSAGE:
            key = _msg_key(
                payload.get("case_id", ""), payload.get("model_key", ""),
                payload.get("role", ""), payload.get("phase"), payload.get("round"),
            )
            src_msg = msg_map.get(key)
            if src_msg is not None:
                await self._repo.add_message(
                    run_id=self._run_id, case_id=src_msg.case_id,
                    model_key=src_msg.model_key, role=src_msg.role,
                    content=src_msg.content, phase=src_msg.phase, round=src_msg.round,
                )
                await self._repo.commit()
            else:
                logger.warning("replay: source message missing for key %s", key)
            await self._emit(etype, payload)

        elif etype == EventType.CASE_SCORED:
            rkey = _result_key(payload.get("case_id", ""), payload.get("model_key", ""))
            src_result = result_map.get(rkey)
            if src_result is not None:
                await self._repo.add_result(
                    run_id=self._run_id,
                    case_id=src_result.case_id, model_key=src_result.model_key,
                    verdict=src_result.verdict, label=src_result.label,
                    passed=src_result.passed, score=src_result.score,
                    confidence=src_result.confidence,
                    evidence_used_json=src_result.evidence_used_json,
                    critical_fail_reason=src_result.critical_fail_reason,
                    latency_ms=src_result.latency_ms,
                    cost_estimate=src_result.cost_estimate,
                    judge_json=src_result.judge_json,
                )
                await self._repo.commit()
                await self._repo.upsert_case_status(
                    run_id=self._run_id, case_id=src_result.case_id,
                    model_key=src_result.model_key, status=CaseStatus.COMPLETED,
                    finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                await self._repo.commit()
            else:
                logger.warning("replay: source result missing for key %s", rkey)
            await self._emit(etype, payload)

        else:
            # metrics_update, case_phase_started, etc.
            await self._emit(etype, payload)

    # --- helpers ---

    async def _emit(self, event_type: str, payload: dict) -> None:
        await emit_and_persist(self._bus, self._repo, self._run_id, event_type, payload)

    async def _fail(self, reason: str) -> None:
        logger.error("Replay FAILED: run_id=%s reason=%s", self._run_id, reason)
        try:
            await self._repo.update_run_status(
                self._run_id, status=RunStatus.FAILED, finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            await self._repo.commit()
            await self._emit(EventType.RUN_FINISHED, {"run_id": self._run_id, "error": reason})
        except Exception:
            logger.exception("couldn't even mark replay as FAILED")

    async def _build_message_map(self) -> dict[tuple, RunMessageRow]:
        msgs = await self._repo.get_all_run_messages(self._source_run_id)
        lookup: dict[tuple, RunMessageRow] = {}
        for m in msgs:
            key = _msg_key(m.case_id, m.model_key, m.role, m.phase, m.round)
            lookup[key] = m  # last-write wins
        return lookup

    async def _build_result_map(self) -> dict[tuple, RunResultRow]:
        results = await self._repo.get_all_run_results(self._source_run_id)
        return {_result_key(r.case_id, r.model_key): r for r in results}


def _compute_delays(events: list[RunEventRow]) -> list[float]:
    """Proportional per-event delays, capped at MAX_REPLAY_SECONDS total."""
    n = len(events)
    if n <= 1:
        return [0.0] * n

    first_ts = events[0].created_at
    last_ts = events[-1].created_at
    original_span = (last_ts - first_ts).total_seconds()

    if original_span <= 0:
        return [0.0] + [MIN_EVENT_DELAY] * (n - 1)

    scale = min(1.0, MAX_REPLAY_SECONDS / original_span)

    delays = [0.0]
    for i in range(1, n):
        delta = (events[i].created_at - events[i - 1].created_at).total_seconds()
        clamped = max(MIN_EVENT_DELAY, min(MAX_EVENT_DELAY, delta * scale))
        delays.append(clamped)

    return delays
