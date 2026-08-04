"""SQLAlchemy 2.x async ORM models."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional


def _utcnow() -> datetime:
    """Naive UTC timestamp compatible with TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.domain.schemas import EvalMode, RunStatus, RunType, ScoringMode


class Base(DeclarativeBase):
    pass


# --- datasets ---

class DatasetRow(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    meta_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    cases: Mapped[list["DatasetCaseRow"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetCaseRow(Base):
    __tablename__ = "dataset_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("datasets.id"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    topic: Mapped[str] = mapped_column(String(256), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    pressure_score: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, nullable=False)
    safe_to_answer: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    dataset: Mapped["DatasetRow"] = relationship(back_populates="cases")

    __table_args__ = (
        Index("ix_dataset_cases_dataset_case", "dataset_id", "case_id"),
    )


# --- runs ---

class RunRow(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("datasets.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=RunStatus.PENDING)
    models_json: Mapped[list] = mapped_column(JSON, nullable=False)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scoring_mode: Mapped[str] = mapped_column(
        String(32), default=ScoringMode.DETERMINISTIC.value, server_default=ScoringMode.DETERMINISTIC.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    case_statuses: Mapped[list["RunCaseStatusRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    messages: Mapped[list["RunMessageRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    results: Mapped[list["RunResultRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    events: Mapped[list["RunEventRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class RunCaseStatusRow(Base):
    __tablename__ = "run_case_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.run_id"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=RunStatus.PENDING)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    run: Mapped["RunRow"] = relationship(back_populates="case_statuses")

    __table_args__ = (
        Index("ix_rcs_run_case_model", "run_id", "case_id", "model_key"),
    )


# --- messages ---

class RunMessageRow(Base):
    __tablename__ = "run_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.run_id"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    phase: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    round: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    run: Mapped["RunRow"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_rm_run_case", "run_id", "case_id"),
    )


# --- results ---

class RunResultRow(Base):
    __tablename__ = "run_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.run_id"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_used_json: Mapped[list] = mapped_column(JSON, nullable=False)
    critical_fail_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    judge_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    run: Mapped["RunRow"] = relationship(back_populates="results")

    __table_args__ = (
        Index("ix_rr_run_model", "run_id", "model_key"),
    )


# --- events ---

class RunEventRow(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.run_id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    run: Mapped["RunRow"] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_re_run_seq", "run_id", "seq"),
    )


# --- cache slots ---

CACHE_SLOT_TTL = timedelta(hours=24)


def _default_expires_at() -> datetime:
    return _utcnow() + CACHE_SLOT_TTL


class CachedResultSetRow(Base):
    __tablename__ = "cached_result_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("datasets.id"), nullable=False
    )
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    slot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.run_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, default=_default_expires_at)
    last_served_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "model_key", "case_id", "slot_number",
            name="uq_cache_slot",
        ),
        Index("ix_cache_dataset_model_case_exp", "dataset_id", "model_key", "case_id", "expires_at"),
    )


# --- galileo analytics ---

import uuid as _uuid
from decimal import Decimal


def _gen_uuid() -> _uuid.UUID:
    return _uuid.uuid4()


def _utcnow_tz() -> datetime:
    return datetime.now(timezone.utc)


class LLMModelRow(Base):
    __tablename__ = "llm_model"

    id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=_gen_uuid,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow_tz,
    )

    eval_runs: Mapped[list["GalileoEvalRunRow"]] = relationship(
        back_populates="llm_model",
    )


class GalileoEvalRunRow(Base):
    __tablename__ = "galileo_eval_run"

    run_id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=_gen_uuid,
    )
    llm_id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("llm_model.id"), nullable=False,
    )
    dataset_id: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    eval_mode: Mapped[str] = mapped_column(
        Text, default=EvalMode.GALILEO.value, nullable=False,
    )
    score_total: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    score_components: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    failure_flags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    run_type: Mapped[str] = mapped_column(
        Text, default=RunType.USER.value, nullable=False,
    )
    benchmark_tag: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    batch_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True,
    )
    source_run_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    app_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    git_sha: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow_tz,
    )

    llm_model: Mapped["LLMModelRow"] = relationship(back_populates="eval_runs")
    payload: Mapped[Optional["GalileoEvalPayloadRow"]] = relationship(
        back_populates="eval_run", uselist=False,
    )

    __table_args__ = (
        Index("ix_ger_llm_created", "llm_id", "created_at"),
        Index("ix_ger_runtype_tag", "run_type", "benchmark_tag", "created_at"),
        Index("ix_ger_eval_mode", "eval_mode", "created_at"),
        Index("ix_ger_ds_case", "dataset_id", "case_id", "created_at"),
    )


class GalileoEvalPayloadRow(Base):
    __tablename__ = "galileo_eval_payload"

    run_id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("galileo_eval_run.run_id", ondelete="CASCADE"),
        primary_key=True,
    )
    result_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    eval_run: Mapped["GalileoEvalRunRow"] = relationship(
        back_populates="payload",
    )


class DebateUsageRow(Base):
    __tablename__ = "debate_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("model_key", "usage_date", name="uq_debate_usage_model_date"),
        Index("ix_debate_usage_model_date", "model_key", "usage_date"),
    )

