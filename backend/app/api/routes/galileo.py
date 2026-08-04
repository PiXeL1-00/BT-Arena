"""Galileo analytics API routes."""

from __future__ import annotations

import asyncio
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.security import verify_admin_key

from app.api.galileo_schemas import (
    CalibrationPoint,
    CalibrationResponse,
    CostPerPassItem,
    CostPerPassResponse,
    DashboardResponse,
    DistributionItem,
    DistributionResponse,
    FailureBreakdownItem,
    FailuresResponse,
    HallucinationTrendBucket,
    HallucinationTrendResponse,
    HallucinationTrendSeries,
    HeatmapCell,
    HeatmapResponse,
    ModelsSummaryResponse,
    ModelSummaryItem,
    ParetoItem,
    ParetoResponse,
    RadarEntry,
    RadarResponse,
    ScoreBreakdownItem,
    ScoreBreakdownResponse,
    SweepTriggerResponse,
    TrendBucket,
    TrendResponse,
    UpliftItem,
    UpliftResponse,
)
from app.config import settings
from app.core.domain.schemas import INACTIVITY_THRESHOLD_DAYS
from app.infra.db.galileo_repository import GalileoRepository
from app.infra.db.session import async_session_factory, get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/galileo", tags=["galileo"])

_summary_cache: dict[str, tuple[float, ModelsSummaryResponse]] = {}
_trend_cache: dict[str, tuple[float, TrendResponse]] = {}
_dashboard_cache: dict[str, tuple[float, DashboardResponse]] = {}


def _cache_key(*parts: object) -> str:
    return ":".join(str(p) for p in parts)


# --- 0. Dashboard (batched) ---

async def _fetch_summary(
    *, window: int, include_scheduled: bool,
) -> ModelsSummaryResponse:
    async with async_session_factory() as s:
        repo = GalileoRepository(s)
        rows = await repo.get_models_summary(
            window_days=window,
            include_scheduled=include_scheduled,
        )
    stale_cutoff_days = INACTIVITY_THRESHOLD_DAYS
    models = []
    for r in rows:
        is_stale = False
        if r.get("last_run_at"):
            from datetime import datetime as dt, timedelta, timezone as tz
            ts = r["last_run_at"]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=tz.utc)
            is_stale = (dt.now(tz.utc) - ts) > timedelta(days=stale_cutoff_days)
        elif r.get("all_time_runs", 0) == 0:
            is_stale = True
        models.append(ModelSummaryItem(
            llm_id=r["id"], provider=r["provider"],
            model_name=r["model_name"], display_name=r["display_name"],
            is_active=r["is_active"],
            all_time_avg=float(r["all_time_avg"]) if r.get("all_time_avg") is not None else None,
            all_time_runs=r.get("all_time_runs") or 0,
            last_run_at=r.get("last_run_at"),
            window_avg=float(r["window_avg"]) if r.get("window_avg") is not None else None,
            window_runs=r.get("window_runs") or 0,
            is_stale=is_stale,
        ))
    return ModelsSummaryResponse(models=models, window_days=window, include_scheduled=include_scheduled)


async def _fetch_trend(
    *, window: int, include_scheduled: bool,
) -> TrendResponse:
    async with async_session_factory() as s:
        repo = GalileoRepository(s)
        rows = await repo.get_models_trend(
            window_days=window,
            include_scheduled=include_scheduled,
        )
    from app.api.galileo_schemas import ModelTrendSeries
    by_llm: dict[UUID, list[TrendBucket]] = {}
    for r in rows:
        lid = r["llm_id"]
        by_llm.setdefault(lid, []).append(
            TrendBucket(bucket=r["bucket"], score_avg=float(r["score_avg"]) if r.get("score_avg") is not None else None, n=r.get("n", 0)),
        )
    series = [ModelTrendSeries(llm_id=lid, buckets=b) for lid, b in by_llm.items()]
    return TrendResponse(series=series, window_days=window)


async def _fetch_distribution(
    *, window: int, include_scheduled: bool,
) -> DistributionResponse:
    async with async_session_factory() as s:
        repo = GalileoRepository(s)
        rows = await repo.get_models_distribution(
            window_days=window,
            include_scheduled=include_scheduled,
        )
    return DistributionResponse(items=[DistributionItem(**r) for r in rows])


async def _fetch_breakdown(
    *, window: int, include_scheduled: bool,
) -> ScoreBreakdownResponse:
    async with async_session_factory() as s:
        repo = GalileoRepository(s)
        rows = await repo.get_score_breakdown(
            window_days=window,
            include_scheduled=include_scheduled,
        )
    return ScoreBreakdownResponse(items=[ScoreBreakdownItem(**r) for r in rows])


async def _fetch_radar(
    *, window: int, include_scheduled: bool,
) -> RadarResponse:
    async with async_session_factory() as s:
        repo = GalileoRepository(s)
        rows = await repo.get_dimensions_radar(
            window_days=window,
            include_scheduled=include_scheduled,
        )
    return RadarResponse(entries=[RadarEntry(**r) for r in rows])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    window: int = Query(default=30, ge=1, le=365),
    include_scheduled: bool = Query(default=False),
) -> DashboardResponse:
    ck = _cache_key("dashboard", window, include_scheduled)
    cached = _dashboard_cache.get(ck)
    if cached and time.time() - cached[0] < settings.analytics_cache_ttl_s:
        return cached[1]

    summary, trend, distribution, breakdown, radar = await asyncio.gather(
        _fetch_summary(window=window, include_scheduled=include_scheduled),
        _fetch_trend(window=window, include_scheduled=include_scheduled),
        _fetch_distribution(window=window, include_scheduled=include_scheduled),
        _fetch_breakdown(window=window, include_scheduled=include_scheduled),
        _fetch_radar(window=window, include_scheduled=include_scheduled),
    )

    resp = DashboardResponse(
        summary=summary, trend=trend, distribution=distribution,
        breakdown=breakdown, radar=radar,
    )
    _dashboard_cache[ck] = (time.time(), resp)
    return resp


# --- 1. Models Summary ---

@router.get("/models/summary", response_model=ModelsSummaryResponse)
async def get_models_summary(
    window: int = Query(default=7, ge=1, le=365),
    include_scheduled: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> ModelsSummaryResponse:
    ck = _cache_key("summary", window, include_scheduled)
    cached = _summary_cache.get(ck)
    if cached and time.time() - cached[0] < settings.analytics_cache_ttl_s:
        return cached[1]

    repo = GalileoRepository(session)
    rows = await repo.get_models_summary(
        window_days=window,
        include_scheduled=include_scheduled,
        timeout_s=settings.analytics_timeout_summary_s,
    )

    stale_cutoff_days = INACTIVITY_THRESHOLD_DAYS
    models = []
    for r in rows:
        is_stale = False
        if r.get("last_run_at"):
            from datetime import datetime, timedelta, timezone
            age = datetime.now(timezone.utc) - r["last_run_at"].replace(
                tzinfo=__import__("datetime").timezone.utc
            ) if r["last_run_at"].tzinfo is None else datetime.now(timezone.utc) - r["last_run_at"]
            is_stale = age > timedelta(days=stale_cutoff_days)
        elif r.get("all_time_runs", 0) == 0:
            is_stale = True

        models.append(ModelSummaryItem(
            llm_id=r["id"],
            provider=r["provider"],
            model_name=r["model_name"],
            display_name=r["display_name"],
            is_active=r["is_active"],
            all_time_avg=float(r["all_time_avg"]) if r.get("all_time_avg") is not None else None,
            all_time_runs=r.get("all_time_runs") or 0,
            last_run_at=r.get("last_run_at"),
            window_avg=float(r["window_avg"]) if r.get("window_avg") is not None else None,
            window_runs=r.get("window_runs") or 0,
            is_stale=is_stale,
        ))

    resp = ModelsSummaryResponse(
        models=models, window_days=window, include_scheduled=include_scheduled,
    )
    _summary_cache[ck] = (time.time(), resp)
    return resp


# --- 2. Models Trend ---

@router.get("/models/trend", response_model=TrendResponse)
async def get_models_trend(
    window: int = Query(default=30, ge=1, le=365),
    bucket: int = Query(default=1, ge=1, le=30),
    llm_ids: str | None = Query(default=None),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> TrendResponse:
    parsed_ids = _parse_uuid_list(llm_ids)
    repo = GalileoRepository(session)
    rows = await repo.get_models_trend(
        window_days=window,
        bucket_days=bucket,
        llm_ids=parsed_ids,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_trend_s,
    )

    by_llm: dict[UUID, list[TrendBucket]] = {}
    for r in rows:
        lid = r["llm_id"]
        if lid not in by_llm:
            by_llm[lid] = []
        by_llm[lid].append(TrendBucket(
            bucket=r["bucket"],
            score_avg=float(r["score_avg"]) if r.get("score_avg") is not None else None,
            n=r.get("n", 0),
        ))

    from app.api.galileo_schemas import ModelTrendSeries
    series = [
        ModelTrendSeries(llm_id=lid, buckets=buckets)
        for lid, buckets in by_llm.items()
    ]
    return TrendResponse(series=series, window_days=window)


# --- 3. Distribution ---

@router.get("/models/distribution", response_model=DistributionResponse)
async def get_models_distribution(
    window: int = Query(default=30, ge=1, le=365),
    llm_ids: str | None = Query(default=None),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> DistributionResponse:
    parsed_ids = _parse_uuid_list(llm_ids)
    repo = GalileoRepository(session)
    rows = await repo.get_models_distribution(
        window_days=window,
        llm_ids=parsed_ids,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_distribution_s,
    )
    items = [DistributionItem(**r) for r in rows]
    return DistributionResponse(items=items)


# --- 4. Heatmap ---

@router.get("/heatmap/model_case", response_model=HeatmapResponse)
async def get_heatmap(
    dataset_id: str = Query(...),
    window: int = Query(default=30, ge=1, le=30),
    top_k: int = Query(default=50, ge=1, le=200),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> HeatmapResponse:
    repo = GalileoRepository(session)
    rows = await repo.get_heatmap_model_case(
        window_days=window,
        dataset_id=dataset_id,
        top_k=top_k,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_heatmap_s,
    )
    cells = [HeatmapCell(**r) for r in rows]
    return HeatmapResponse(cells=cells, dataset_id=dataset_id, top_k=top_k)


# --- 5. Radar ---

@router.get("/dimensions/radar", response_model=RadarResponse)
async def get_radar(
    window: int = Query(default=30, ge=1, le=365),
    llm_ids: str | None = Query(default=None),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> RadarResponse:
    parsed_ids = _parse_uuid_list(llm_ids)
    repo = GalileoRepository(session)
    rows = await repo.get_dimensions_radar(
        window_days=window,
        llm_ids=parsed_ids,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_default_s,
    )
    entries = [RadarEntry(**r) for r in rows]
    return RadarResponse(entries=entries)


# --- 6. Uplift ---

@router.get("/effect/uplift", response_model=UpliftResponse)
async def get_uplift(
    window: int = Query(default=30, ge=1, le=365),
    include_scheduled: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> UpliftResponse:
    repo = GalileoRepository(session)
    rows = await repo.get_uplift(
        window_days=window,
        include_scheduled=include_scheduled,
        timeout_s=settings.analytics_timeout_default_s,
    )
    items = []
    for r in rows:
        avg_b = float(r["avg_baseline"]) if r.get("avg_baseline") is not None else None
        avg_g = float(r["avg_galileo"]) if r.get("avg_galileo") is not None else None
        delta = (avg_g - avg_b) if avg_b is not None and avg_g is not None else None
        items.append(UpliftItem(
            llm_id=r["llm_id"],
            avg_baseline=avg_b,
            avg_galileo=avg_g,
            n_pairs=r.get("n_pairs", 0),
            delta=delta,
        ))
    return UpliftResponse(items=items)


# --- 7. Failures ---

@router.get("/failures/breakdown", response_model=FailuresResponse)
async def get_failures(
    window: int = Query(default=30, ge=1, le=30),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> FailuresResponse:
    repo = GalileoRepository(session)
    rows = await repo.get_failures_breakdown(
        window_days=window,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_default_s,
    )
    items = [FailureBreakdownItem(**r) for r in rows]
    return FailuresResponse(items=items)


# --- 8. Pareto ---

@router.get("/ops/pareto", response_model=ParetoResponse)
async def get_pareto(
    window: int = Query(default=30, ge=1, le=30),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> ParetoResponse:
    repo = GalileoRepository(session)
    rows = await repo.get_ops_pareto(
        window_days=window,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_default_s,
    )
    items = [ParetoItem(**r) for r in rows]
    return ParetoResponse(items=items)


# --- 9. Score Breakdown ---

@router.get("/dimensions/breakdown", response_model=ScoreBreakdownResponse)
async def get_score_breakdown(
    window: int = Query(default=30, ge=1, le=365),
    llm_ids: str | None = Query(default=None),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> ScoreBreakdownResponse:
    parsed_ids = _parse_uuid_list(llm_ids)
    repo = GalileoRepository(session)
    rows = await repo.get_score_breakdown(
        window_days=window,
        llm_ids=parsed_ids,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_default_s,
    )
    items = [ScoreBreakdownItem(**r) for r in rows]
    return ScoreBreakdownResponse(items=items)


# --- 10. Hallucination Trend ---

@router.get("/hallucination/trend", response_model=HallucinationTrendResponse)
async def get_hallucination_trend(
    window: int = Query(default=30, ge=1, le=365),
    llm_ids: str | None = Query(default=None),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> HallucinationTrendResponse:
    parsed_ids = _parse_uuid_list(llm_ids)
    repo = GalileoRepository(session)
    rows = await repo.get_hallucination_trend(
        window_days=window,
        llm_ids=parsed_ids,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_default_s,
    )

    by_llm: dict[UUID, list[HallucinationTrendBucket]] = {}
    for r in rows:
        lid = r["llm_id"]
        by_llm.setdefault(lid, []).append(HallucinationTrendBucket(
            bucket=r["bucket"],
            hallucination_rate=r.get("hallucination_rate"),
            n=r.get("n", 0),
        ))

    series = [
        HallucinationTrendSeries(llm_id=lid, buckets=buckets)
        for lid, buckets in by_llm.items()
    ]
    return HallucinationTrendResponse(series=series, window_days=window)


# --- 11. Calibration Scatter ---

@router.get("/calibration/scatter", response_model=CalibrationResponse)
async def get_calibration_scatter(
    window: int = Query(default=30, ge=1, le=365),
    llm_ids: str | None = Query(default=None),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> CalibrationResponse:
    parsed_ids = _parse_uuid_list(llm_ids)
    repo = GalileoRepository(session)
    rows = await repo.get_calibration_scatter(
        window_days=window,
        llm_ids=parsed_ids,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_default_s,
    )
    points = [CalibrationPoint(**r) for r in rows]
    return CalibrationResponse(points=points)


# --- 12. Cost per Pass ---

@router.get("/ops/cost_per_pass", response_model=CostPerPassResponse)
async def get_cost_per_pass(
    window: int = Query(default=30, ge=1, le=365),
    llm_ids: str | None = Query(default=None),
    include_scheduled: bool = Query(default=False),
    eval_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> CostPerPassResponse:
    parsed_ids = _parse_uuid_list(llm_ids)
    repo = GalileoRepository(session)
    rows = await repo.get_cost_per_pass(
        window_days=window,
        llm_ids=parsed_ids,
        include_scheduled=include_scheduled,
        eval_mode=eval_mode,
        timeout_s=settings.analytics_timeout_default_s,
    )
    items = [CostPerPassItem(**r) for r in rows]
    return CostPerPassResponse(items=items)


# --- 13. Admin: Trigger Sweep ---

@router.post("/admin/run_freshness_sweep", response_model=SweepTriggerResponse)
async def run_freshness_sweep(
    session: AsyncSession = Depends(get_session),
    _: None = Depends(verify_admin_key),
) -> SweepTriggerResponse:
    from app.usecases.freshness_sweep import run_freshness_sweep

    result = await run_freshness_sweep(session)
    return SweepTriggerResponse(**result)


# --- helpers ---

def _parse_uuid_list(raw: str | None) -> list[UUID] | None:
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [UUID(p) for p in parts] if parts else None
