"""One-time backfill: run_results → galileo_eval_run.

Usage: python -m scripts.backfill_eval_runs
"""

from __future__ import annotations

import asyncio
import logging
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.model_identity import parse_model_key
from app.core.domain.schemas import EvalMode, RunType
from app.infra.db.galileo_repository import GalileoRepository
from app.infra.db.models import GalileoEvalRunRow, RunResultRow, RunRow
from app.infra.db.session import async_session_factory

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_BATCH_SIZE = 500


async def backfill(session: AsyncSession) -> int:
    stmt = (
        select(RunResultRow, RunRow)
        .join(RunRow, RunResultRow.run_id == RunRow.run_id)
        .order_by(RunResultRow.id)
    )
    result = await session.execute(stmt)
    rows = result.all()

    repo = GalileoRepository(session)
    inserted = 0

    for rr, run in rows:
        try:
            identity = parse_model_key(rr.model_key)
        except Exception:
            logger.warning("Skipping unparseable model_key=%s", rr.model_key)
            continue

        llm = await repo.find_or_create_llm(
            provider=identity.provider,
            model_name=identity.model_name,
            model_version=identity.version,
        )

        score_components = None
        if rr.judge_json and isinstance(rr.judge_json, dict):
            score_components = rr.judge_json.get("score_breakdown")

        failure_flags = None
        if rr.critical_fail_reason:
            failure_flags = {"critical_fail": rr.critical_fail_reason}

        row = GalileoEvalRunRow(
            llm_id=llm.id,
            dataset_id=run.dataset_id,
            case_id=run.case_id,
            eval_mode=EvalMode.GALILEO.value,
            score_total=Decimal(str(rr.score)),
            score_components=score_components,
            failure_flags=failure_flags,
            run_type=RunType.BACKFILL.value,
            source_run_id=run.run_id,
            latency_ms=rr.latency_ms,
            cost_usd=Decimal(str(rr.cost_estimate)) if rr.cost_estimate else None,
        )
        session.add(row)

        inserted += 1
        if inserted % _BATCH_SIZE == 0:
            try:
                await session.flush()
                logger.info("Flushed %d rows", inserted)
            except Exception:
                await session.rollback()
                logger.warning("Batch conflict at %d, continuing", inserted)

    await session.commit()
    return inserted


async def main() -> None:
    async with async_session_factory() as session:
        count = await backfill(session)
        logger.info("Backfill complete: %d rows inserted", count)


if __name__ == "__main__":
    asyncio.run(main())
