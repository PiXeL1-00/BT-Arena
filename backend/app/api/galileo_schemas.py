"""Pydantic v2 response schemas for Galileo analytics endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ModelSummaryItem(BaseModel):
    llm_id: UUID
    provider: str
    model_name: str
    display_name: str
    is_active: bool
    all_time_avg: float | None = None
    all_time_runs: int = 0
    last_run_at: datetime | None = None
    window_avg: float | None = None
    window_runs: int = 0
    is_stale: bool = False


class ModelsSummaryResponse(BaseModel):
    models: list[ModelSummaryItem]
    window_days: int
    include_scheduled: bool


class TrendBucket(BaseModel):
    bucket: datetime
    score_avg: float | None = None
    n: int = 0


class ModelTrendSeries(BaseModel):
    llm_id: UUID
    buckets: list[TrendBucket]


class TrendResponse(BaseModel):
    series: list[ModelTrendSeries]
    window_days: int


class DistributionItem(BaseModel):
    llm_id: UUID
    mean: float | None = None
    stddev: float | None = None
    n: int = 0
    p10: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    p90: float | None = None


class DistributionResponse(BaseModel):
    items: list[DistributionItem]


class HeatmapCell(BaseModel):
    llm_id: UUID
    case_id: str
    avg_score: float | None = None
    n: int = 0


class HeatmapResponse(BaseModel):
    cells: list[HeatmapCell]
    dataset_id: str
    top_k: int


class RadarEntry(BaseModel):
    llm_id: UUID
    dimension: str
    avg_value: float | None = None
    n: int = 0


class RadarResponse(BaseModel):
    entries: list[RadarEntry]


class UpliftItem(BaseModel):
    llm_id: UUID
    avg_baseline: float | None = None
    avg_galileo: float | None = None
    n_pairs: int = 0
    delta: float | None = None


class UpliftResponse(BaseModel):
    items: list[UpliftItem]


class FailureBreakdownItem(BaseModel):
    llm_id: UUID
    failure_type: str
    count: int


class FailuresResponse(BaseModel):
    items: list[FailureBreakdownItem]


class ParetoItem(BaseModel):
    llm_id: UUID
    avg_score: float | None = None
    avg_latency_ms: float | None = None
    avg_cost_usd: float | None = None
    n: int = 0


class ParetoResponse(BaseModel):
    items: list[ParetoItem]


class SweepTriggerResponse(BaseModel):
    status: str
    models_swept: int = 0
    evals_run: int = 0
    message: str = ""


class ScoreBreakdownItem(BaseModel):
    llm_id: UUID
    correctness: float = 0.0
    grounding: float = 0.0
    calibration: float = 0.0
    falsifiable: float = 0.0
    deference_penalty: float = 0.0
    refusal_penalty: float = 0.0
    n: int = 0


class ScoreBreakdownResponse(BaseModel):
    items: list[ScoreBreakdownItem]


class HallucinationTrendBucket(BaseModel):
    bucket: datetime
    hallucination_rate: float | None = None
    n: int = 0


class HallucinationTrendSeries(BaseModel):
    llm_id: UUID
    buckets: list[HallucinationTrendBucket]


class HallucinationTrendResponse(BaseModel):
    series: list[HallucinationTrendSeries]
    window_days: int


class CalibrationPoint(BaseModel):
    llm_id: UUID
    score_total: float
    calibration: float


class CalibrationResponse(BaseModel):
    points: list[CalibrationPoint]


class CostPerPassItem(BaseModel):
    llm_id: UUID
    cost_per_pass: float | None = None
    total_cost: float = 0.0
    passing_runs: int = 0
    total_runs: int = 0


class CostPerPassResponse(BaseModel):
    items: list[CostPerPassItem]


class DashboardResponse(BaseModel):
    summary: ModelsSummaryResponse
    trend: TrendResponse
    distribution: DistributionResponse
    breakdown: ScoreBreakdownResponse
    radar: RadarResponse
