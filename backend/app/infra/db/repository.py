"""Thin persistence adapter -- single repo for all tables (PoC simplicity)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, delete, desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.domain.schemas import RunStatus

from .models import (
    CachedResultSetRow,
    DatasetCaseRow,
    DatasetRow,
    DebateUsageRow,
    RunCaseStatusRow,
    RunEventRow,
    RunMessageRow,
    RunResultRow,
    RunRow,
)

logger = logging.getLogger(__name__)


class Repository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # --- datasets ---

    async def dataset_exists(self, dataset_id: str) -> bool:
        stmt = select(DatasetRow.id).where(DatasetRow.id == dataset_id)
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_dataset_version_only(self, dataset_id: str) -> Optional[str]:
        """Get dataset version without loading cases. Returns None if not found.
        
        This avoids eager loading that pollutes the session with case objects,
        which can cause session state corruption when deleting and recreating datasets.
        
        Use this instead of get_dataset() when you only need the version.
        """
        stmt = select(DatasetRow.version).where(DatasetRow.id == dataset_id)
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def create_dataset(
        self,
        *,
        dataset_id: str,
        version: str,
        description: str,
        meta_json: dict,
    ) -> None:
        row = DatasetRow(
            id=dataset_id, version=version,
            description=description, meta_json=meta_json,
        )
        self._s.add(row)
        await self._s.flush()

    async def create_dataset_case(
        self,
        *,
        dataset_id: str,
        case_id: str,
        topic: str,
        claim: str,
        pressure_score: int,
        label: str,
        evidence_json: list[dict],
        safe_to_answer: bool = True,
    ) -> None:
        row = DatasetCaseRow(
            dataset_id=dataset_id, case_id=case_id,
            topic=topic, claim=claim,
            pressure_score=pressure_score, label=label,
            evidence_json=evidence_json,
            safe_to_answer=safe_to_answer,
        )
        self._s.add(row)
        await self._s.flush()

    async def list_datasets(self) -> list[DatasetRow]:
        stmt = (
            select(DatasetRow)
            .order_by(DatasetRow.created_at.desc())
            .options(selectinload(DatasetRow.cases))
        )
        result = await self._s.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_dataset(self, dataset_id: str) -> Optional[DatasetRow]:
        stmt = (
            select(DatasetRow)
            .where(DatasetRow.id == dataset_id)
            .options(selectinload(DatasetRow.cases))
        )
        result = await self._s.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_dataset_cases(self, dataset_id: str) -> list[DatasetCaseRow]:
        stmt = (
            select(DatasetCaseRow)
            .where(DatasetCaseRow.dataset_id == dataset_id)
            .order_by(DatasetCaseRow.id)
        )
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    async def get_dataset_case(
        self, dataset_id: str, case_id: str,
    ) -> Optional[DatasetCaseRow]:
        stmt = select(DatasetCaseRow).where(and_(
            DatasetCaseRow.dataset_id == dataset_id,
            DatasetCaseRow.case_id == case_id,
        ))
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset and all its cases.
        
        IMPORTANT: 
        - Core-level delete() statements don't trigger ORM relationship cascades
        - PostgreSQL FK constraints (without ON DELETE CASCADE) prevent parent deletion if children exist
        - We must explicitly delete in order: cases → cache slots → dataset
        
        If runs reference this dataset, an IntegrityError will be raised (by design - preserves data integrity).
        """
        # Delete cases first (PostgreSQL FK constraint requires this)
        # Core delete doesn't trigger ORM cascade, so explicit deletion is necessary
        cases_stmt = delete(DatasetCaseRow).where(
            DatasetCaseRow.dataset_id == dataset_id
        )
        await self._s.execute(cases_stmt)
        
        # Delete cache slots (they reference datasets via FK without CASCADE)
        cache_stmt = delete(CachedResultSetRow).where(
            CachedResultSetRow.dataset_id == dataset_id
        )
        await self._s.execute(cache_stmt)
        
        # Now safe to delete dataset (no FK constraint violations)
        stmt = delete(DatasetRow).where(DatasetRow.id == dataset_id)
        await self._s.execute(stmt)
        await self._s.flush()

    # --- runs ---

    async def create_run(
        self,
        *,
        run_id: str,
        dataset_id: str,
        case_id: str,
        models_json: list[dict],
        scoring_mode: Optional[str] = None,
    ) -> None:
        from app.config import settings
        
        # Set scoring_mode explicitly (fallback to config if not provided)
        if scoring_mode is None:
            from app.core.domain.schemas import ScoringMode
            scoring_mode = ScoringMode.ML.value if settings.ml_scoring_enabled else ScoringMode.DETERMINISTIC.value
        
        row = RunRow(
            run_id=run_id,
            dataset_id=dataset_id,
            case_id=case_id,
            models_json=models_json,
            status=RunStatus.PENDING,
            scoring_mode=scoring_mode,
        )
        self._s.add(row)
        try:
            await self._s.flush()
        except Exception as e:
            logger.error(
                "Failed to create run: run_id=%s, dataset_id=%s, case_id=%s, error=%s",
                run_id, dataset_id, case_id, e,
                exc_info=True,
            )
            raise

    async def get_run(self, run_id: str) -> Optional[RunRow]:
        stmt = select(RunRow).where(RunRow.run_id == run_id)
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def update_run_status(
        self,
        run_id: str,
        *,
        status: str,
        finished_at: Optional[datetime] = None,
    ) -> None:
        stmt = select(RunRow).where(RunRow.run_id == run_id)
        result = await self._s.execute(stmt)
        row = result.scalar_one()
        row.status = status
        if finished_at:
            row.finished_at = finished_at
        await self._s.flush()

    # --- case status ---

    async def upsert_case_status(
        self,
        *,
        run_id: str,
        case_id: str,
        model_key: str,
        status: str,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
    ) -> None:
        stmt = select(RunCaseStatusRow).where(
            and_(
                RunCaseStatusRow.run_id == run_id,
                RunCaseStatusRow.case_id == case_id,
                RunCaseStatusRow.model_key == model_key,
            )
        )
        result = await self._s.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            row = RunCaseStatusRow(
                run_id=run_id, case_id=case_id, model_key=model_key,
                status=status, started_at=started_at,
            )
            self._s.add(row)
        else:
            row.status = status
            if started_at:
                row.started_at = started_at
            if finished_at:
                row.finished_at = finished_at
        await self._s.flush()

    # --- messages ---

    async def add_message(
        self,
        *,
        run_id: str,
        case_id: str,
        model_key: str,
        role: str,
        content: str,
        phase: Optional[str] = None,
        round: Optional[int] = None,
    ) -> None:
        row = RunMessageRow(
            run_id=run_id, case_id=case_id, model_key=model_key,
            role=role, content=content, phase=phase, round=round,
        )
        self._s.add(row)
        await self._s.flush()

    async def get_case_messages(
        self, run_id: str, case_id: str
    ) -> list[RunMessageRow]:
        stmt = (
            select(RunMessageRow)
            .where(and_(
                RunMessageRow.run_id == run_id,
                RunMessageRow.case_id == case_id,
            ))
            .order_by(RunMessageRow.created_at)
        )
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    # --- results ---

    # pass-through -- caller owns the shape
    async def add_result(self, **kwargs) -> None:
        row = RunResultRow(**kwargs)
        self._s.add(row)
        await self._s.flush()

    async def get_run_results(
        self,
        run_id: str,
        *,
        model_key: Optional[str] = None,
        case_id: Optional[str] = None,
    ) -> list[RunResultRow]:
        conditions = [RunResultRow.run_id == run_id]
        if model_key:
            conditions.append(RunResultRow.model_key == model_key)
        if case_id:
            conditions.append(RunResultRow.case_id == case_id)
        stmt = (
            select(RunResultRow)
            .where(and_(*conditions))
            .order_by(RunResultRow.created_at)
        )
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    # --- events (SSE) ---

    async def add_event(
        self,
        *,
        run_id: str,
        seq: int,
        event_type: str,
        payload_json: dict,
    ) -> None:
        row = RunEventRow(
            run_id=run_id, seq=seq,
            event_type=event_type, payload_json=payload_json,
        )
        self._s.add(row)
        await self._s.flush()

    async def get_events_since(
        self, run_id: str, *, from_seq: int = 0, limit: int = 200
    ) -> list[RunEventRow]:
        stmt = (
            select(RunEventRow)
            .where(and_(
                RunEventRow.run_id == run_id,
                RunEventRow.seq > from_seq,
            ))
            .order_by(RunEventRow.seq)
            .limit(limit)
        )
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    async def get_max_event_seq(self, run_id: str) -> int:
        stmt = (
            select(RunEventRow.seq)
            .where(RunEventRow.run_id == run_id)
            .order_by(desc(RunEventRow.seq))
            .limit(1)
        )
        result = await self._s.execute(stmt)
        return result.scalar() or 0

    # --- cache slots ---

    async def get_next_cache_slot_to_serve(
        self,
        dataset_id: str,
        model_key: str,
        case_id: str,
    ) -> Optional[CachedResultSetRow]:
        """Next non-expired slot, round-robin by last_served_at."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            select(CachedResultSetRow)
            .where(and_(
                CachedResultSetRow.dataset_id == dataset_id,
                CachedResultSetRow.model_key == model_key,
                CachedResultSetRow.case_id == case_id,
                CachedResultSetRow.expires_at > now,
            ))
            .order_by(
                CachedResultSetRow.last_served_at.asc().nulls_first(),
                CachedResultSetRow.slot_number.asc(),
            )
            .limit(1)
        )
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_slot_served(self, slot_id: int) -> None:
        stmt = select(CachedResultSetRow).where(CachedResultSetRow.id == slot_id)
        result = await self._s.execute(stmt)
        row = result.scalar_one()
        row.last_served_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self._s.flush()

    async def get_next_empty_slot_number(
        self,
        dataset_id: str,
        model_key: str,
        case_id: str,
        *,
        max_slots: int,
    ) -> Optional[int]:
        """First slot in 1..max_slots not occupied by a live (non-expired) row."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            select(CachedResultSetRow.slot_number)
            .where(and_(
                CachedResultSetRow.dataset_id == dataset_id,
                CachedResultSetRow.model_key == model_key,
                CachedResultSetRow.case_id == case_id,
                CachedResultSetRow.expires_at > now,
            ))
        )
        result = await self._s.execute(stmt)
        occupied = {row for row in result.scalars().all()}
        for n in range(1, max_slots + 1):
            if n not in occupied:
                return n
        return None

    async def create_cache_slot(
        self,
        *,
        dataset_id: str,
        model_key: str,
        case_id: str,
        slot_number: int,
        source_run_id: str,
    ) -> bool:
        """Returns True on insert, False on unique-constraint conflict."""
        from .models import _default_expires_at

        row = CachedResultSetRow(
            dataset_id=dataset_id, model_key=model_key,
            case_id=case_id, slot_number=slot_number,
            source_run_id=source_run_id,
            expires_at=_default_expires_at(),
        )
        self._s.add(row)
        try:
            await self._s.flush()
            return True
        except IntegrityError:
            await self._s.rollback()
            logger.warning(
                "cache slot conflict: dataset=%s model=%s case=%s slot=%d",
                dataset_id, model_key, case_id, slot_number,
            )
            return False

    async def delete_all_cache_slots(self) -> int:
        stmt = delete(CachedResultSetRow)
        result = await self._s.execute(stmt)
        await self._s.flush()
        return result.rowcount  # type: ignore[return-value]

    async def delete_expired_slots(self) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = delete(CachedResultSetRow).where(CachedResultSetRow.expires_at <= now)
        result = await self._s.execute(stmt)
        await self._s.flush()
        return result.rowcount  # type: ignore[return-value]

    # --- bulk (replay) ---

    async def get_all_run_events(self, run_id: str) -> list[RunEventRow]:
        stmt = select(RunEventRow).where(RunEventRow.run_id == run_id).order_by(RunEventRow.seq)
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    async def get_all_run_messages(self, run_id: str) -> list[RunMessageRow]:
        stmt = select(RunMessageRow).where(RunMessageRow.run_id == run_id).order_by(RunMessageRow.id)
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    async def get_all_run_results(self, run_id: str) -> list[RunResultRow]:
        stmt = select(RunResultRow).where(RunResultRow.run_id == run_id).order_by(RunResultRow.id)
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    # --- debate usage tracking ---

    async def get_debate_usage_today(
        self, model_key: str, *, today: date,
    ) -> int:
        stmt = select(DebateUsageRow.call_count).where(
            and_(DebateUsageRow.model_key == model_key, DebateUsageRow.usage_date == today),
        )
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none() or 0

    async def increment_debate_usage(
        self, model_key: str, *, today: date,
    ) -> int:
        """Atomic upsert: INSERT ... ON CONFLICT DO UPDATE SET call_count = call_count + 1."""
        stmt = (
            pg_insert(DebateUsageRow)
            .values(model_key=model_key, usage_date=today, call_count=1)
            .on_conflict_do_update(
                constraint="uq_debate_usage_model_date",
                set_={"call_count": DebateUsageRow.call_count + 1},
            )
            .returning(DebateUsageRow.call_count)
        )
        result = await self._s.execute(stmt)
        await self._s.flush()
        return result.scalar_one()

    async def check_and_increment_debate_usage(
        self, model_key: str, *, today: date, cap: int,
    ) -> tuple[bool, int]:
        """Atomically increment usage and check cap.

        Returns (allowed, new_count). If new_count > cap after increment,
        the increment is still committed — caller should rollback if needed.
        """
        new_count = await self.increment_debate_usage(model_key, today=today)
        return new_count <= cap, new_count

    async def get_all_debate_usage_today(
        self, *, today: date,
    ) -> dict[str, int]:
        stmt = select(DebateUsageRow).where(DebateUsageRow.usage_date == today)
        result = await self._s.execute(stmt)
        return {r.model_key: r.call_count for r in result.scalars().all()}

    async def commit(self) -> None:
        await self._s.commit()
