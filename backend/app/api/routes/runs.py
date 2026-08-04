from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.config import settings
from app.core.domain.exceptions import DailyCapExceededError, ModelNotAllowedError
from app.core.domain.schemas import RunRequest, RunStatus
from app.infra.db.repository import Repository
from app.infra.sse.event_bus import event_bus
from app.infra.timezone_utils import get_today_in_tz
from app.usecases.compute_summary import compute_run_summary
from app.usecases.replay_cached import ReplayCachedUsecase
from app.usecases.run_eval import RunEvalUsecase

router = APIRouter(prefix="/runs", tags=["runs"])
_log = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
_run_semaphore = asyncio.Semaphore(settings.max_concurrent_runs)

_ERR_SERVER_BUSY = "Server busy — too many concurrent runs. Try again shortly."

_ERR_MODEL_NOT_ALLOWED = (
    "Model '{}' is not available in production mode. Allowed: {}"
)
_ERR_DAILY_CAP_REACHED = (
    "Daily cap ({}) reached for '{}'. Resets tomorrow ({})."
)


async def _enforce_and_record_prod_usage(
    repo: Repository,
    models: list[dict],
) -> None:
    """Atomically validate allowlist + increment daily usage in prod mode.

    Does nothing in debug mode. Raises ModelNotAllowedError or
    DailyCapExceededError for violations.
    """
    if settings.debug:
        return

    allowed = settings.debate_enabled_production_model_keys
    today = get_today_in_tz()
    cap = settings.debate_daily_production_cap

    for m in models:
        model_key = f"{m['provider']}/{m['model_name']}"
        if model_key not in allowed:
            raise ModelNotAllowedError(model_key)
        ok, _count = await repo.check_and_increment_debate_usage(
            model_key, today=today, cap=cap,
        )
        if not ok:
            raise DailyCapExceededError(model_key, cap=cap)


async def _compute_total_cost(session: AsyncSession, run_id: str) -> float:
    repo = Repository(session)
    results = await repo.get_run_results(run_id)
    return round(sum(float(r.cost_estimate) for r in results), 6)


async def _try_cache_slot(
    repo: Repository,
    dataset_id: str,
    models: list[dict],
    case_id: str,
) -> Optional[str]:
    """Only fires when STORE_RESULT=true and exactly 1 model is selected.
    Returns source_run_id or None."""
    if not settings.store_result or len(models) != 1:
        return None

    model_key = f"{models[0]['provider']}/{models[0]['model_name']}"
    slot = await repo.get_next_cache_slot_to_serve(dataset_id, model_key, case_id)
    if slot is None:
        return None

    source_run = await repo.get_run(slot.source_run_id)
    if source_run is None or source_run.status != RunStatus.COMPLETED:
        _log.warning("cache slot %d stale (source=%s), skipping", slot.slot_number, slot.source_run_id)
        return None

    await repo.mark_slot_served(slot.id)
    await repo.commit()
    return slot.source_run_id


async def _prepare_run(
    repo: Repository,
    body: RunRequest,
) -> tuple[str, list[dict], Optional[str]]:
    """Shared prep for both POST endpoints: validate dataset + case, enforce
    prod limits, create run row, check cache."""
    ds = await repo.get_dataset(body.dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    case_row = await repo.get_dataset_case(body.dataset_id, body.case_id)
    if case_row is None:
        raise HTTPException(404, "Case not found in dataset")

    models = [m.model_dump(mode="json") for m in body.models]

    # prod-mode: atomic allowlist check + usage increment
    try:
        await _enforce_and_record_prod_usage(repo, models)
    except ModelNotAllowedError as exc:
        raise HTTPException(403, _ERR_MODEL_NOT_ALLOWED.format(
            exc.model_key, ", ".join(settings.debate_enabled_production_model_keys),
        )) from exc
    except DailyCapExceededError as exc:
        raise HTTPException(429, _ERR_DAILY_CAP_REACHED.format(
            exc.cap, exc.model_key, settings.app_timezone,
        )) from exc

    run_id = str(uuid.uuid4())
    models_json = [{"provider": m["provider"], "model_name": m["model_name"]} for m in models]

    await repo.create_run(
        run_id=run_id,
        dataset_id=body.dataset_id,
        case_id=body.case_id,
        models_json=models_json,
    )

    await repo.commit()

    source_run_id = await _try_cache_slot(repo, body.dataset_id, models, body.case_id)
    return run_id, models, source_run_id


# --- POST /runs ---

@router.post("")
@limiter.limit(settings.rate_limit_runs)
async def create_run(
    request: Request,
    body: RunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    from app.infra.db.session import async_session_factory

    repo = Repository(session)
    run_id, models, source_run_id = await _prepare_run(repo, body)

    if source_run_id is not None:
        _log.info("Cache HIT: run_id=%s replaying source=%s", run_id, source_run_id)

        async def _replay():
            try:
                async with async_session_factory() as bg_session:
                    uc = ReplayCachedUsecase(bg_session, event_bus, run_id=run_id, source_run_id=source_run_id)
                    await uc.execute()
            finally:
                event_bus.cleanup_run(run_id)

        background_tasks.add_task(_replay)
    else:
        _log.info(
            "Cache MISS: run_id=%s, dataset=%s, case=%s, models=%s",
            run_id, body.dataset_id, body.case_id,
            [m.get("model_name") for m in models],
        )

        async def _run():
            async with _run_semaphore:
                try:
                    async with async_session_factory() as bg_session:
                        uc = RunEvalUsecase(bg_session, event_bus)
                        await uc.execute(
                            dataset_id=body.dataset_id,
                            case_id=body.case_id,
                            models=models,
                            run_id=run_id,
                        )
                        _log.info("Background task done: run_id=%s", run_id)
                except Exception as exc:
                    _log.exception("Background task blew up: run_id=%s error=%s", run_id, exc)
                    raise
                finally:
                    event_bus.cleanup_run(run_id)

        background_tasks.add_task(_run)

    total_cost = await _compute_total_cost(session, run_id)
    return {
        "run_id": run_id,
        "status": RunStatus.PENDING.value,
        "message": "Run queued",
        "total_llm_cost": total_cost,
    }


# --- POST /runs/start ---

@router.post("/start")
@limiter.limit(settings.rate_limit_runs)
async def start_run_sync(
    request: Request,
    body: RunRequest,
    session: AsyncSession = Depends(get_session),
):
    from app.infra.db.session import async_session_factory

    repo = Repository(session)
    run_id, models, source_run_id = await _prepare_run(repo, body)

    if source_run_id is not None:
        _log.info("Cache HIT: run_id=%s replaying source=%s", run_id, source_run_id)

        async def _replay():
            try:
                async with async_session_factory() as bg_session:
                    uc = ReplayCachedUsecase(bg_session, event_bus, run_id=run_id, source_run_id=source_run_id)
                    await uc.execute()
            finally:
                event_bus.cleanup_run(run_id)

        asyncio.create_task(_replay())
    else:
        _log.info(
            "Cache MISS: run_id=%s, dataset=%s, case=%s, models=%s",
            run_id, body.dataset_id, body.case_id,
            [m.get("model_name") for m in models],
        )

        async def _run():
            try:
                async with async_session_factory() as bg_session:
                    uc = RunEvalUsecase(bg_session, event_bus)
                    await uc.execute(
                        dataset_id=body.dataset_id,
                        case_id=body.case_id,
                        models=models,
                        run_id=run_id,
                    )
            finally:
                event_bus.cleanup_run(run_id)

        asyncio.create_task(_run())

    return {
        "run_id": run_id,
        "status": RunStatus.PENDING.value,
        "message": "Run started in background",
        "total_llm_cost": 0.0,
    }


# --- GET endpoints ---

@router.get("/{run_id}")
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
):
    repo = Repository(session)
    run = await repo.get_run(run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    total_cost = await _compute_total_cost(session, run_id)
    return {
        "run_id": run.run_id,
        "dataset_id": run.dataset_id,
        "status": run.status,
        "models": run.models_json,
        "case_id": run.case_id,
        "created_at": run.created_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "total_llm_cost": total_cost,
        "debug_mode": settings.debug_mode,
    }


@router.get("/{run_id}/summary")
async def get_run_summary(
    run_id: str,
    session: AsyncSession = Depends(get_session),
):
    summary = await compute_run_summary(session, run_id)
    total_cost = await _compute_total_cost(session, run_id)
    out = summary.model_dump()
    out["total_llm_cost"] = total_cost
    out["debug_mode"] = settings.debug_mode
    return out


@router.get("/{run_id}/cases")
async def get_run_cases(
    run_id: str,
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    repo = Repository(session)
    results = await repo.get_run_results(run_id, model_key=model)

    if status == "pass":
        results = [r for r in results if r.passed]
    elif status == "fail":
        results = [r for r in results if not r.passed]

    total = len(results)
    page = results[skip : skip + limit]
    total_cost = await _compute_total_cost(session, run_id)

    return {
        "total": total,
        "total_llm_cost": total_cost,
        "cases": [
            {
                "case_id": r.case_id,
                "model_key": r.model_key,
                "verdict": r.verdict,
                "label": r.label,
                "score": r.score,
                "passed": r.passed,
                "confidence": r.confidence,
                "latency_ms": r.latency_ms,
                "critical_fail_reason": r.critical_fail_reason,
            }
            for r in page
        ],
    }


@router.get("/{run_id}/cases/{case_id}")
async def get_case_replay(
    run_id: str,
    case_id: str,
    model: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    repo = Repository(session)
    messages = await repo.get_case_messages(run_id, case_id)
    results = await repo.get_run_results(run_id, case_id=case_id, model_key=model)

    if not results:
        raise HTTPException(404, "Case not found in this run")

    total_cost = await _compute_total_cost(session, run_id)

    return {
        "case_id": case_id,
        "total_llm_cost": total_cost,
        "messages": [
            {
                "role": m.role,
                "model_key": m.model_key,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "results": [
            {
                "model_key": r.model_key,
                "verdict": r.verdict,
                "label": r.label,
                "score": r.score,
                "passed": r.passed,
                "confidence": r.confidence,
                "judge_json": r.judge_json,
                "critical_fail_reason": r.critical_fail_reason,
                "latency_ms": r.latency_ms,
                "cost_estimate": float(r.cost_estimate),
            }
            for r in results
        ],
    }


@router.get("/{run_id}/messages")
async def get_run_messages(
    run_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get all historical messages for a run (for completed runs)."""
    repo = Repository(session)
    messages = await repo.get_all_run_messages(run_id)
    return [
        {
            "role": m.role,
            "model_key": m.model_key,
            "content": m.content,
            "phase": m.phase,
            "round": m.round,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.get("/{run_id}/events")
async def stream_events(run_id: str):
    return StreamingResponse(
        event_bus.stream(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
