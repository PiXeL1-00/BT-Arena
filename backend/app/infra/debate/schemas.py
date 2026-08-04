"""Infra-only schemas used between debate phases (final judge uses core JudgeDecision)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Literal

from pydantic import BaseModel, Field, model_validator

from app.core.domain.schemas import DebateRole, VerdictEnum


class DebatePhase(str, Enum):
    SETUP = "setup"
    INDEPENDENT = "independent"
    CROSS_EXAM = "cross_exam"
    REVISION = "revision"
    DISPUTE = "dispute"
    JUDGE = "judge"


class AdmissionLevel(str, Enum):
    NONE = "none"
    INSUFFICIENT = "insufficient"
    UNCERTAIN = "uncertain"


# Module-level constants for admission values (avoid hardcoded strings)
_ADM_NONE = AdmissionLevel.NONE.value
_ADM_INSUFFICIENT = AdmissionLevel.INSUFFICIENT.value
_ADM_UNCERTAIN = AdmissionLevel.UNCERTAIN.value


class DebateTarget(str, Enum):
    HERETIC = DebateRole.HERETIC.value
    ORTHODOX = DebateRole.ORTHODOX.value
    BOTH = "Both"


class LogMessageType(str, Enum):
    QUESTIONS = "questions"
    ANSWERS = "answers"


# keep Literals for Pydantic field validation (backed by enums above)
VERDICT_LITERAL = Literal["SUPPORTED", "REFUTED", "INSUFFICIENT"]
ADMISSION_LITERAL = Literal["none", "insufficient", "uncertain"]
TARGET_LITERAL = Literal["Heretic", "Orthodox", "Both"]

FALLBACK_QUESTION = "Unable to generate question"
FALLBACK_ANSWER = "Unable to generate answer"
FALLBACK_JUDGE_REASONING = "Failed to parse judge output"


# --- phase 1: proposals ---

class Proposal(BaseModel):
    proposed_verdict: VERDICT_LITERAL
    evidence_used: list[str] = Field(min_length=0)
    key_points: list[str] = Field(min_length=1)
    uncertainties: list[str] = Field(default_factory=list)
    what_would_change_my_mind: list[str] = Field(default_factory=list)


# --- phase 2: cross-exam ---

class Question(BaseModel):
    to: TARGET_LITERAL
    q: str
    evidence_refs: list[str] = Field(default_factory=list)


class QuestionsMessage(BaseModel):
    questions: list[Question] = Field(min_length=1, max_length=2)


class Answer(BaseModel):
    q: str
    a: str
    evidence_refs: list[str] = Field(default_factory=list)
    admission: ADMISSION_LITERAL = Field(default=AdmissionLevel.NONE)
    
    @model_validator(mode="before")
    @classmethod
    def ensure_admission(cls, data: dict) -> dict:  # type: ignore[type-arg]
        """Ensure admission is never None or missing."""
        if isinstance(data, dict):
            if "admission" not in data or data.get("admission") is None:
                data = {**data, "admission": _ADM_NONE}
        return data


class AnswersMessage(BaseModel):
    answers: list[Answer] = Field(min_length=1, max_length=2)


# --- phase 3: revision ---

class Revision(BaseModel):
    final_proposed_verdict: VERDICT_LITERAL
    evidence_used: list[str] = Field(min_length=0)
    what_i_changed: list[str] = Field(default_factory=list)
    remaining_disagreements: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


# --- phase 3.5: dispute ---

class DisputeQuestion(BaseModel):
    q: str
    evidence_refs: list[str] = Field(default_factory=list)


class DisputeQuestionsMessage(BaseModel):
    questions: list[DisputeQuestion] = Field(min_length=1, max_length=1)


class DisputeAnswer(BaseModel):
    q: str
    a: str
    evidence_refs: list[str] = Field(default_factory=list)
    admission: ADMISSION_LITERAL = Field(default=AdmissionLevel.NONE)
    
    @model_validator(mode="before")
    @classmethod
    def ensure_admission(cls, data: dict) -> dict:  # type: ignore[type-arg]
        """Ensure admission is never None or missing."""
        if isinstance(data, dict):
            if "admission" not in data or data.get("admission") is None:
                data = {**data, "admission": _ADM_NONE}
        return data


class DisputeAnswersMessage(BaseModel):
    answers: list[DisputeAnswer] = Field(min_length=1, max_length=1)


# --- shared memo (deterministic, no LLM) ---

@dataclass
class SharedMemo:
    all_evidence_cited: set[str]
    verdicts_by_role: dict[str, str]
    contested_points: list[str]

    def to_context_str(self) -> str:
        lines = [
            "=== Shared Memo ===",
            f"Evidence cited so far: {sorted(self.all_evidence_cited)}",
            f"Current verdicts: {self.verdicts_by_role}",
        ]
        if self.contested_points:
            lines.append(f"Contested points: {self.contested_points[:5]}")
        return "\n".join(lines)


# --- callback events ---

@dataclass(frozen=True)
class MessageEvent:
    case_id: str
    role: str
    content: str
    phase: str
    round: int


@dataclass(frozen=True)
class PhaseEvent:
    case_id: str
    phase: str


# --- debate result types (shared between FSM and AutoGen controllers) ---

@dataclass
class DebateMessage:
    role: str
    content: str
    phase: str = ""
    round: int = 0


@dataclass
class DebateResult:
    messages: list[DebateMessage] = field(default_factory=list)
    judge_json: dict[str, str | float | list[str]] = field(default_factory=dict)
    total_latency_ms: int = 0
    total_cost: float = 0.0


OnMessageCallback = Callable[[MessageEvent], None]
OnPhaseCallback = Callable[[PhaseEvent], None]
