from __future__ import annotations

from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.metrics import compute_model_metrics
from app.core.domain.schemas import CaseResultEntry, ModelMetrics, RunStatus, RunSummary
from app.infra.db.repository import Repository

DEFAULT_PRESSURE = 5


async def compute_run_summary(session: AsyncSession, run_id: str) -> RunSummary:
    repo = Repository(session)
    run = await repo.get_run(run_id)
    results = await repo.get_run_results(run_id)

    by_model: dict[str, list[CaseResultEntry]] = defaultdict(list)
    for r in results:
        by_model[r.model_key].append(CaseResultEntry(
            case_id=r.case_id,
            score=r.score,
            passed=r.passed,
            critical_fail_reason=r.critical_fail_reason,
            latency_ms=r.latency_ms,
            cost_estimate=float(r.cost_estimate),
            pressure_score=DEFAULT_PRESSURE,
        ))

    dataset_id = run.dataset_id if run else ""
    cases = await repo.get_dataset_cases(dataset_id)
    pressure_map = {c.case_id: c.pressure_score for c in cases}

    # Re-create entries with correct pressure scores (frozen dataclass)
    for mk in by_model:
        by_model[mk] = [
            CaseResultEntry(
                case_id=e.case_id,
                score=e.score,
                passed=e.passed,
                critical_fail_reason=e.critical_fail_reason,
                latency_ms=e.latency_ms,
                cost_estimate=e.cost_estimate,
                pressure_score=pressure_map.get(e.case_id, DEFAULT_PRESSURE),
            )
            for e in by_model[mk]
        ]

    models: list[ModelMetrics] = [
        compute_model_metrics(mk, entries) for mk, entries in by_model.items()
    ]

    return RunSummary(
        run_id=run_id,
        status=run.status if run else RunStatus.FAILED,
        total_cases=len(results),
        models=models,
    )

