"""Auto-freshness sweep: run real evaluations for stale LLMs.

Calls the actual debate pipeline — no synthetic scores.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.domain.schemas import (
    BENCHMARK_TAG_AUTO_SWEEP,
    INACTIVITY_THRESHOLD_DAYS,
    RunType,
)
from app.infra.db.galileo_repository import GalileoRepository
from app.infra.db.repository import Repository

logger = logging.getLogger(__name__)

_SWEEP_LOCK_KEY = "galileo_auto_sweep"


def select_deterministic_cases(
    seed_date: str,
    pool: list[dict],
    *,
    n: int = 5,
) -> list[dict]:
    """MD5-seeded deterministic selection, stratified across datasets.

    Each dict in pool must have 'dataset_id' and 'case_id'.
    """
    if len(pool) <= n:
        return pool

    by_dataset: dict[str, list[dict]] = {}
    for item in pool:
        ds = item["dataset_id"]
        if ds not in by_dataset:
            by_dataset[ds] = []
        by_dataset[ds].append(item)

    for ds in by_dataset:
        by_dataset[ds].sort(
            key=lambda x: hashlib.md5(
                f"{seed_date}:{x['dataset_id']}:{x['case_id']}".encode()
            ).hexdigest()
        )

    selected: list[dict] = []
    datasets = sorted(by_dataset.keys())
    idx = 0
    while len(selected) < n:
        ds = datasets[idx % len(datasets)]
        ds_cases = by_dataset[ds]
        if ds_cases:
            selected.append(ds_cases.pop(0))
        else:
            datasets.remove(ds)
            if not datasets:
                break
        idx += 1

    return selected[:n]


def build_idempotency_key(
    *,
    date: str,
    llm_id: str,
    eval_mode: str,
    dataset_id: str,
    case_id: str,
) -> str:
    return f"{BENCHMARK_TAG_AUTO_SWEEP}:{date}:{llm_id}:{eval_mode}:{dataset_id}:{case_id}"


async def run_freshness_sweep(session: AsyncSession) -> dict:
    """Run freshness sweep. Returns status dict for API response."""
    repo = GalileoRepository(session)

    locked = await repo.try_advisory_xact_lock(lock_key=_SWEEP_LOCK_KEY)
    if not locked:
        logger.info("Sweep already in progress, skipping")
        return {"status": "skipped", "message": "Another sweep is in progress"}

    inactive = await repo.find_inactive_models(
        threshold_days=INACTIVITY_THRESHOLD_DAYS,
    )
    if not inactive:
        logger.info("No inactive models found, nothing to sweep")
        return {"status": "ok", "models_swept": 0, "evals_run": 0, "message": "No stale models"}

    base_repo = Repository(session)
    from app.infra.db.session import async_session_factory

    datasets = await base_repo.list_datasets()
    case_pool: list[dict] = []
    for ds in datasets:
        for case in ds.cases:
            case_pool.append({
                "dataset_id": ds.id,
                "case_id": case.case_id,
            })

    if not case_pool:
        return {"status": "ok", "models_swept": 0, "evals_run": 0, "message": "No cases available"}

    seed = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cases = select_deterministic_cases(
        seed, case_pool, n=settings.sweep_cases_count,
    )

    batch_id = str(uuid.uuid4())
    semaphore = asyncio.Semaphore(settings.sweep_max_parallel)
    total_cost = 0.0
    evals_run = 0
    max_evals = settings.sweep_max_evals_per_run

    async def run_single_eval(
        model_row, case_info: dict, eval_mode: str,
    ) -> None:
        nonlocal total_cost, evals_run

        if evals_run >= max_evals:
            return
        if total_cost >= settings.sweep_max_cost_usd:
            logger.warning("Sweep budget exceeded (%.2f USD), aborting", total_cost)
            return

        idem_key = build_idempotency_key(
            date=seed,
            llm_id=str(model_row.id),
            eval_mode=eval_mode,
            dataset_id=case_info["dataset_id"],
            case_id=case_info["case_id"],
        )

        async with semaphore:
            try:
                async with async_session_factory() as eval_session:
                    from app.usecases.run_eval import RunEvalUsecase
                    from app.infra.sse.event_bus import EventBus

                    bus = EventBus()
                    usecase = RunEvalUsecase(eval_session, bus)
                    await usecase.execute(
                        dataset_id=case_info["dataset_id"],
                        case_id=case_info["case_id"],
                        models=[{
                            "provider": model_row.provider,
                            "model_name": model_row.model_name,
                        }],
                    )
                    evals_run += 1
            except Exception:
                logger.warning(
                    "Sweep eval failed: model=%s case=%s",
                    model_row.display_name, case_info["case_id"],
                    exc_info=True,
                )

    for model in inactive:
        for case_info in cases:
            await run_single_eval(model, case_info, "galileo")
            if settings.sweep_include_baseline:
                await run_single_eval(model, case_info, "baseline")

    logger.info(
        "Sweep complete: models=%d evals=%d",
        len(inactive), evals_run,
    )
    return {
        "status": "ok",
        "models_swept": len(inactive),
        "evals_run": evals_run,
        "message": f"Swept {len(inactive)} models, ran {evals_run} evaluations",
    }
