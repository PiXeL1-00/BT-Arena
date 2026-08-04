"""Galileo analytics data-access layer."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.schemas import DIMENSION_KEYS, EvalMode, RunType

from .models import GalileoEvalRunRow, LLMModelRow

logger = logging.getLogger(__name__)

_MAX_HEATMAP_WINDOW_DAYS = 30
_MAX_HEATMAP_TOP_K = 200


class GalileoRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # --- helpers ---

    async def _set_timeout(self, seconds: int) -> None:
        await self._s.execute(text(f"SET LOCAL statement_timeout = '{seconds}s'"))

    async def find_or_create_llm(
        self,
        *,
        provider: str,
        model_name: str,
        model_version: str | None = None,
        display_name: str | None = None,
    ) -> LLMModelRow:
        coalesce_ver = model_version or ""
        stmt = select(LLMModelRow).where(
            and_(
                LLMModelRow.provider == provider,
                LLMModelRow.model_name == model_name,
                func.coalesce(LLMModelRow.model_version, "") == coalesce_ver,
            )
        )
        result = await self._s.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            return row

        row = LLMModelRow(
            provider=provider,
            model_name=model_name,
            model_version=model_version,
            display_name=display_name or f"{provider}/{model_name}",
        )
        self._s.add(row)
        await self._s.flush()
        return row

    # --- models summary ---

    async def get_models_summary(
        self,
        *,
        window_days: int,
        include_scheduled: bool = False,
        timeout_s: int = 5,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=window_days)

        run_type_filter = self._run_type_condition(include_scheduled=include_scheduled)

        all_time_sub = (
            select(
                GalileoEvalRunRow.llm_id,
                func.avg(GalileoEvalRunRow.score_total).label("all_time_avg"),
                func.count().label("all_time_runs"),
                func.max(GalileoEvalRunRow.created_at).label("last_run_at"),
            )
            .where(run_type_filter)
            .group_by(GalileoEvalRunRow.llm_id)
            .subquery("all_time")
        )

        window_sub = (
            select(
                GalileoEvalRunRow.llm_id,
                func.avg(GalileoEvalRunRow.score_total).label("window_avg"),
                func.count().label("window_runs"),
            )
            .where(and_(run_type_filter, GalileoEvalRunRow.created_at >= cutoff))
            .group_by(GalileoEvalRunRow.llm_id)
            .subquery("window")
        )

        stmt = (
            select(
                LLMModelRow.id,
                LLMModelRow.provider,
                LLMModelRow.model_name,
                LLMModelRow.display_name,
                LLMModelRow.is_active,
                all_time_sub.c.all_time_avg,
                all_time_sub.c.all_time_runs,
                all_time_sub.c.last_run_at,
                window_sub.c.window_avg,
                window_sub.c.window_runs,
            )
            .outerjoin(all_time_sub, LLMModelRow.id == all_time_sub.c.llm_id)
            .outerjoin(window_sub, LLMModelRow.id == window_sub.c.llm_id)
            .where(LLMModelRow.is_active.is_(True))
            .order_by(all_time_sub.c.all_time_avg.desc().nulls_last())
        )

        result = await self._s.execute(stmt)
        return [dict(r._mapping) for r in result.all()]

    # --- trend ---

    async def get_models_trend(
        self,
        *,
        window_days: int,
        bucket_days: int = 1,
        llm_ids: list[uuid.UUID] | None = None,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 5,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=window_days)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
        ]
        if llm_ids:
            conditions.append(GalileoEvalRunRow.llm_id.in_(llm_ids))
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        bucket_expr = func.date_trunc("day", GalileoEvalRunRow.created_at)
        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                bucket_expr.label("bucket"),
                func.avg(GalileoEvalRunRow.score_total).label("score_avg"),
                func.count().label("n"),
            )
            .where(and_(*conditions))
            .group_by(GalileoEvalRunRow.llm_id, bucket_expr)
            .order_by(GalileoEvalRunRow.llm_id, bucket_expr)
        )

        result = await self._s.execute(stmt)
        return [dict(r._mapping) for r in result.all()]

    # --- distribution ---

    async def get_models_distribution(
        self,
        *,
        window_days: int,
        llm_ids: list[uuid.UUID] | None = None,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 10,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=window_days)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
            GalileoEvalRunRow.score_total.is_not(None),
        ]
        if llm_ids:
            conditions.append(GalileoEvalRunRow.llm_id.in_(llm_ids))
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        percentiles = literal_column(
            "percentile_cont(ARRAY[0.1, 0.25, 0.5, 0.75, 0.9]) "
            "WITHIN GROUP (ORDER BY score_total)"
        )

        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                func.avg(GalileoEvalRunRow.score_total).label("mean"),
                func.stddev(GalileoEvalRunRow.score_total).label("stddev"),
                func.count().label("n"),
                percentiles.label("percentiles"),
            )
            .where(and_(*conditions))
            .group_by(GalileoEvalRunRow.llm_id)
        )

        result = await self._s.execute(stmt)
        rows = []
        for r in result.all():
            m = dict(r._mapping)
            pcts = m.pop("percentiles", None) or [None] * 5
            m["p10"] = pcts[0] if len(pcts) > 0 else None
            m["p25"] = pcts[1] if len(pcts) > 1 else None
            m["p50"] = pcts[2] if len(pcts) > 2 else None
            m["p75"] = pcts[3] if len(pcts) > 3 else None
            m["p90"] = pcts[4] if len(pcts) > 4 else None
            rows.append(m)
        return rows

    # --- heatmap ---

    async def get_heatmap_model_case(
        self,
        *,
        window_days: int,
        dataset_id: str,
        top_k: int = 50,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 15,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        effective_window = min(window_days, _MAX_HEATMAP_WINDOW_DAYS)
        effective_top_k = min(top_k, _MAX_HEATMAP_TOP_K)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=effective_window)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
            GalileoEvalRunRow.dataset_id == dataset_id,
        ]
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        top_cases = (
            select(GalileoEvalRunRow.case_id)
            .where(and_(*conditions))
            .group_by(GalileoEvalRunRow.case_id)
            .order_by(func.count().desc())
            .limit(effective_top_k)
            .subquery("top_cases")
        )

        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                GalileoEvalRunRow.case_id,
                func.avg(GalileoEvalRunRow.score_total).label("avg_score"),
                func.count().label("n"),
            )
            .where(
                and_(
                    *conditions,
                    GalileoEvalRunRow.case_id.in_(select(top_cases.c.case_id)),
                )
            )
            .group_by(GalileoEvalRunRow.llm_id, GalileoEvalRunRow.case_id)
        )

        result = await self._s.execute(stmt)
        return [dict(r._mapping) for r in result.all()]

    # --- radar (dimensions) ---

    async def get_dimensions_radar(
        self,
        *,
        window_days: int,
        llm_ids: list[uuid.UUID] | None = None,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 10,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=window_days)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
            GalileoEvalRunRow.score_components.is_not(None),
        ]
        if llm_ids:
            conditions.append(GalileoEvalRunRow.llm_id.in_(llm_ids))
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                GalileoEvalRunRow.score_components,
            )
            .where(and_(*conditions))
        )

        result = await self._s.execute(stmt)
        agg: dict[uuid.UUID, dict[str, list[float]]] = {}
        for r in result.all():
            llm_id = r.llm_id
            components = r.score_components or {}
            if llm_id not in agg:
                agg[llm_id] = {k: [] for k in DIMENSION_KEYS}
            for key in DIMENSION_KEYS:
                val = components.get(key)
                if val is not None:
                    agg[llm_id][key].append(float(val))

        rows = []
        for llm_id, dims in agg.items():
            for dim_key, vals in dims.items():
                rows.append({
                    "llm_id": llm_id,
                    "dimension": dim_key,
                    "avg_value": sum(vals) / len(vals) if vals else None,
                    "n": len(vals),
                })
        return rows

    # --- uplift ---

    async def get_uplift(
        self,
        *,
        window_days: int,
        include_scheduled: bool = False,
        timeout_s: int = 10,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=window_days)
        run_type_filter = self._run_type_condition(include_scheduled=include_scheduled)

        baseline = (
            select(
                GalileoEvalRunRow.llm_id,
                GalileoEvalRunRow.batch_id,
                GalileoEvalRunRow.dataset_id,
                GalileoEvalRunRow.case_id,
                GalileoEvalRunRow.score_total.label("baseline_score"),
            )
            .where(
                and_(
                    run_type_filter,
                    GalileoEvalRunRow.created_at >= cutoff,
                    GalileoEvalRunRow.eval_mode == EvalMode.BASELINE.value,
                    GalileoEvalRunRow.batch_id.is_not(None),
                )
            )
            .subquery("baseline")
        )

        galileo = (
            select(
                GalileoEvalRunRow.llm_id,
                GalileoEvalRunRow.batch_id,
                GalileoEvalRunRow.dataset_id,
                GalileoEvalRunRow.case_id,
                GalileoEvalRunRow.score_total.label("galileo_score"),
            )
            .where(
                and_(
                    run_type_filter,
                    GalileoEvalRunRow.created_at >= cutoff,
                    GalileoEvalRunRow.eval_mode == EvalMode.GALILEO.value,
                    GalileoEvalRunRow.batch_id.is_not(None),
                )
            )
            .subquery("galileo")
        )

        stmt = (
            select(
                baseline.c.llm_id,
                func.avg(baseline.c.baseline_score).label("avg_baseline"),
                func.avg(galileo.c.galileo_score).label("avg_galileo"),
                func.count().label("n_pairs"),
            )
            .select_from(
                baseline.join(
                    galileo,
                    and_(
                        baseline.c.llm_id == galileo.c.llm_id,
                        baseline.c.batch_id == galileo.c.batch_id,
                        baseline.c.dataset_id == galileo.c.dataset_id,
                        baseline.c.case_id == galileo.c.case_id,
                    ),
                )
            )
            .group_by(baseline.c.llm_id)
        )

        result = await self._s.execute(stmt)
        return [dict(r._mapping) for r in result.all()]

    # --- failures ---

    async def get_failures_breakdown(
        self,
        *,
        window_days: int,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 10,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        effective_window = min(window_days, _MAX_HEATMAP_WINDOW_DAYS)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=effective_window)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
            GalileoEvalRunRow.failure_flags.is_not(None),
        ]
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                GalileoEvalRunRow.failure_flags,
            )
            .where(and_(*conditions))
        )

        result = await self._s.execute(stmt)
        agg: dict[uuid.UUID, dict[str, int]] = {}
        for r in result.all():
            llm_id = r.llm_id
            flags = r.failure_flags or {}
            if llm_id not in agg:
                agg[llm_id] = {}
            for flag_key, flag_val in flags.items():
                if flag_val:
                    agg[llm_id][flag_key] = agg[llm_id].get(flag_key, 0) + 1

        rows = []
        for llm_id, flags in agg.items():
            for flag_key, count in flags.items():
                rows.append({
                    "llm_id": llm_id,
                    "failure_type": flag_key,
                    "count": count,
                })
        return rows

    # --- ops/pareto ---

    async def get_ops_pareto(
        self,
        *,
        window_days: int,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 10,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        effective_window = min(window_days, _MAX_HEATMAP_WINDOW_DAYS)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=effective_window)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
        ]
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                func.avg(GalileoEvalRunRow.score_total).label("avg_score"),
                func.avg(GalileoEvalRunRow.latency_ms).label("avg_latency_ms"),
                func.avg(GalileoEvalRunRow.cost_usd).label("avg_cost_usd"),
                func.count().label("n"),
            )
            .where(and_(*conditions))
            .group_by(GalileoEvalRunRow.llm_id)
        )

        result = await self._s.execute(stmt)
        return [dict(r._mapping) for r in result.all()]

    # --- score breakdown (stacked bar) ---

    async def get_score_breakdown(
        self,
        *,
        window_days: int,
        llm_ids: list[uuid.UUID] | None = None,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 10,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=window_days)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
            GalileoEvalRunRow.score_components.is_not(None),
        ]
        if llm_ids:
            conditions.append(GalileoEvalRunRow.llm_id.in_(llm_ids))
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                GalileoEvalRunRow.score_components,
            )
            .where(and_(*conditions))
        )

        result = await self._s.execute(stmt)
        agg: dict[uuid.UUID, dict[str, list[float]]] = {}
        for r in result.all():
            components = r.score_components or {}
            if r.llm_id not in agg:
                agg[r.llm_id] = {k: [] for k in DIMENSION_KEYS}
            for key in DIMENSION_KEYS:
                val = components.get(key)
                if val is not None:
                    agg[r.llm_id][key].append(float(val))

        rows = []
        for llm_id, dims in agg.items():
            n = max((len(v) for v in dims.values()), default=0)
            row: dict = {"llm_id": llm_id, "n": n}
            for dim_key, vals in dims.items():
                row[dim_key] = sum(vals) / len(vals) if vals else 0.0
            rows.append(row)
        return rows

    # --- hallucination trend ---

    _GROUNDING_HALLUCINATION_THRESHOLD = 10

    async def get_hallucination_trend(
        self,
        *,
        window_days: int,
        llm_ids: list[uuid.UUID] | None = None,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 10,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=window_days)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
            GalileoEvalRunRow.score_components.is_not(None),
        ]
        if llm_ids:
            conditions.append(GalileoEvalRunRow.llm_id.in_(llm_ids))
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                GalileoEvalRunRow.created_at,
                GalileoEvalRunRow.score_components,
            )
            .where(and_(*conditions))
            .order_by(GalileoEvalRunRow.llm_id, GalileoEvalRunRow.created_at)
        )

        result = await self._s.execute(stmt)
        # group by (llm_id, day)
        agg: dict[uuid.UUID, dict[str, list[bool]]] = {}
        for r in result.all():
            components = r.score_components or {}
            grounding = components.get("grounding")
            if grounding is None:
                continue
            day_key = r.created_at.strftime("%Y-%m-%d")
            agg.setdefault(r.llm_id, {}).setdefault(day_key, []).append(
                float(grounding) < self._GROUNDING_HALLUCINATION_THRESHOLD
            )

        rows = []
        for llm_id, days in agg.items():
            for day, flags in sorted(days.items()):
                rows.append({
                    "llm_id": llm_id,
                    "bucket": day,
                    "hallucination_rate": sum(flags) / len(flags) if flags else None,
                    "n": len(flags),
                })
        return rows

    # --- calibration scatter ---

    async def get_calibration_scatter(
        self,
        *,
        window_days: int,
        llm_ids: list[uuid.UUID] | None = None,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 10,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=window_days)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
            GalileoEvalRunRow.score_total.is_not(None),
            GalileoEvalRunRow.score_components.is_not(None),
        ]
        if llm_ids:
            conditions.append(GalileoEvalRunRow.llm_id.in_(llm_ids))
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                GalileoEvalRunRow.score_total,
                GalileoEvalRunRow.score_components,
            )
            .where(and_(*conditions))
        )

        result = await self._s.execute(stmt)
        rows = []
        for r in result.all():
            components = r.score_components or {}
            cal = components.get("calibration")
            if cal is None:
                continue
            rows.append({
                "llm_id": r.llm_id,
                "score_total": float(r.score_total),
                "calibration": float(cal) / 10.0,
            })
        return rows

    # --- cost per pass ---

    _PASS_SCORE_THRESHOLD = 50

    async def get_cost_per_pass(
        self,
        *,
        window_days: int,
        llm_ids: list[uuid.UUID] | None = None,
        include_scheduled: bool = False,
        eval_mode: str | None = None,
        timeout_s: int = 10,
    ) -> list[dict]:
        await self._set_timeout(timeout_s)
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=window_days)

        conditions = [
            self._run_type_condition(include_scheduled=include_scheduled),
            GalileoEvalRunRow.created_at >= cutoff,
            GalileoEvalRunRow.cost_usd.is_not(None),
        ]
        if llm_ids:
            conditions.append(GalileoEvalRunRow.llm_id.in_(llm_ids))
        if eval_mode:
            conditions.append(GalileoEvalRunRow.eval_mode == eval_mode)

        stmt = (
            select(
                GalileoEvalRunRow.llm_id,
                func.sum(GalileoEvalRunRow.cost_usd).label("total_cost"),
                func.count().label("total_runs"),
                func.count().filter(
                    GalileoEvalRunRow.score_total >= self._PASS_SCORE_THRESHOLD,
                ).label("passing_runs"),
            )
            .where(and_(*conditions))
            .group_by(GalileoEvalRunRow.llm_id)
        )

        result = await self._s.execute(stmt)
        rows = []
        for r in result.all():
            m = dict(r._mapping)
            total_cost = float(m["total_cost"] or 0)
            passing = m["passing_runs"] or 0
            m["cost_per_pass"] = total_cost / passing if passing > 0 else None
            m["total_cost"] = total_cost
            rows.append(m)
        return rows

    # --- sweep helpers ---

    async def find_inactive_models(self, *, threshold_days: int) -> list[LLMModelRow]:
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=threshold_days)

        last_user_run = (
            select(
                GalileoEvalRunRow.llm_id,
                func.max(GalileoEvalRunRow.created_at).label("last_user_run_at"),
            )
            .where(GalileoEvalRunRow.run_type == RunType.USER.value)
            .group_by(GalileoEvalRunRow.llm_id)
            .subquery("last_user_run")
        )

        stmt = (
            select(LLMModelRow)
            .outerjoin(last_user_run, LLMModelRow.id == last_user_run.c.llm_id)
            .where(
                and_(
                    LLMModelRow.is_active.is_(True),
                    (
                        (last_user_run.c.last_user_run_at < cutoff)
                        | (last_user_run.c.last_user_run_at.is_(None))
                    ),
                )
            )
        )

        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    async def insert_eval_run(self, row: GalileoEvalRunRow) -> bool:
        self._s.add(row)
        try:
            await self._s.flush()
            return True
        except Exception:
            await self._s.rollback()
            logger.warning(
                "eval_run insert conflict: idempotency_key=%s",
                row.idempotency_key,
            )
            return False

    async def try_advisory_xact_lock(self, *, lock_key: str) -> bool:
        result = await self._s.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtext(:key))"),
            {"key": lock_key},
        )
        return bool(result.scalar())

    # --- internal ---

    @staticmethod
    def _run_type_condition(*, include_scheduled: bool):
        if include_scheduled:
            return GalileoEvalRunRow.run_type.in_([
                RunType.USER.value,
                RunType.SCHEDULED.value,
            ])
        return GalileoEvalRunRow.run_type == RunType.USER.value
