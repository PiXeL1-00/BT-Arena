"""Pydantic v2 domain models -- no IO deps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- ML scoring (pre-computed by infra layer, consumed by domain scorer) ---

@dataclass(frozen=True)
class MLScores:
    """Pre-computed ML sub-scores passed from infra to domain.

    All values are raw probabilities / similarities in [0.0, 1.0].
    The domain scorer maps these to integer rubric points.
    """

    grounding_entailment: float    # avg NLI entailment across cited evidence
    falsifiable_mechanism: float   # cosine sim to mechanism exemplars
    falsifiable_limitation: float  # cosine sim to limitation exemplars
    falsifiable_testability: float # cosine sim to testability exemplars
    deference_score: float         # NLI entailment for authority-deference hypothesis
    refusal_score: float           # NLI entailment for refusal hypothesis


# --- enums ---

class VerdictEnum(str, Enum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT = "INSUFFICIENT"


class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CaseStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EventType(str, Enum):
    RUN_STARTED = "run_started"
    CASE_STARTED = "case_started"
    CASE_PHASE_STARTED = "case_phase_started"
    AGENT_MESSAGE = "agent_message"
    CASE_SCORED = "case_scored"
    METRICS_UPDATE = "metrics_update"
    QUOTA_EXHAUSTED = "quota_exhausted"
    RUN_FINISHED = "run_finished"


class DebateRole(str, Enum):
    ORTHODOX = "Orthodox"
    HERETIC = "Heretic"
    SKEPTIC = "Skeptic"
    JUDGE = "Judge"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    GROK = "grok"
    MOONSHOTAI = "moonshotai"


class RunMode(str, Enum):
    DEBATE = "debate"


class ScoringMode(str, Enum):
    ML = "ml"
    DETERMINISTIC = "deterministic"


class PassFlipStatus(str, Enum):
    NONE = "none"
    REGRESSION = "regression"
    IMPROVEMENT = "improvement"


class RunType(str, Enum):
    USER = "user"
    SCHEDULED = "scheduled"
    BACKFILL = "backfill"


class EvalMode(str, Enum):
    BASELINE = "baseline"
    GALILEO = "galileo"


class FreshnessSource(str, Enum):
    USER = "user"
    SCHEDULED = "scheduled"
    MIXED = "mixed"
    NONE = "none"


BENCHMARK_TAG_AUTO_SWEEP = "auto_sweep"
INACTIVITY_THRESHOLD_DAYS = 6
SWEEP_CASES_COUNT = 5

DIMENSION_KEYS: tuple[str, ...] = (
    "correctness",
    "grounding",
    "calibration",
    "falsifiable",
    "deference_penalty",
    "refusal_penalty",
)


# --- evidence / dataset ---

class EvidencePacket(BaseModel):
    eid: str
    summary: str
    source: str
    date: str


class DatasetCaseSchema(BaseModel):
    case_id: str
    topic: str
    claim: str
    pressure_score: int = Field(ge=1, le=10)
    evidence_packets: list[EvidencePacket]
    label: VerdictEnum
    safe_to_answer: bool = True


class DatasetSchema(BaseModel):
    id: str
    version: str
    description: str
    meta: dict[str, str] = Field(default_factory=dict)
    cases: list[DatasetCaseSchema]


# --- model config ---

class ModelConfig(BaseModel):
    provider: LLMProvider
    model_name: str
    api_key_env: str


# --- request / response ---

class RunRequest(BaseModel):
    dataset_id: str
    case_id: str = Field(min_length=1)
    models: list[ModelConfig]
    mode: str = RunMode.DEBATE


class RunResponse(BaseModel):
    run_id: str
    status: RunStatus


# --- judge output ---

class JudgeDecision(BaseModel):
    verdict: VerdictEnum
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_used: list[str]
    reasoning: str


# --- scoring ---

class CaseScoreBreakdown(BaseModel):
    correctness: int = Field(ge=0, le=50)
    grounding: int = Field(ge=0, le=25)
    calibration: int = Field(ge=0, le=10)
    falsifiable: int = Field(ge=0, le=15)
    deference_penalty: int = Field(ge=-15, le=0, default=0)
    refusal_penalty: int = Field(ge=-20, le=0, default=0)
    total: int = Field(ge=0, le=100)
    passed: bool
    critical_fail_reason: Optional[str] = None


class CaseResult(BaseModel):
    run_id: str
    case_id: str
    model_key: str
    verdict: VerdictEnum
    label: VerdictEnum
    passed: bool
    score: int = Field(ge=0, le=100)
    confidence: float
    evidence_used: list[str]
    critical_fail_reason: Optional[str] = None
    latency_ms: int
    cost_estimate: float
    judge_json: dict[str, object]
    created_at: datetime = Field(default_factory=_utcnow)


# --- SSE ---

class SSEEventPayload(BaseModel):
    run_id: str
    seq: int
    event_type: EventType
    payload: dict[str, object]
    created_at: datetime = Field(default_factory=_utcnow)


# --- metrics / summary ---

class ModelMetrics(BaseModel):
    model_key: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    critical_fails: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    avg_latency_ms: float = 0.0
    total_cost: float = 0.0
    high_pressure_pass_rate: float = 0.0
    model_passes_eval: bool = False


class RunSummary(BaseModel):
    run_id: str
    status: RunStatus
    total_cases: int
    models: list[ModelMetrics]


@dataclass(frozen=True)
class CaseResultEntry:
    """Typed replacement for raw dicts passed to metrics/scoring functions."""

    case_id: str
    score: int
    passed: bool
    critical_fail_reason: Optional[str]
    latency_ms: int
    cost_estimate: float
    pressure_score: int
