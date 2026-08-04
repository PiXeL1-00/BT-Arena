"""Per-model metrics aggregation -- pure functions over typed results."""

from __future__ import annotations

from .schemas import CaseResultEntry, ModelMetrics
from .scoring import HIGH_PRESSURE_THRESHOLD, model_passes_eval


def compute_model_metrics(
    model_key: str,
    results: list[CaseResultEntry],
) -> ModelMetrics:
    if not results:
        return ModelMetrics(model_key=model_key)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    critical = sum(1 for r in results if r.critical_fail_reason)
    scores = [r.score for r in results]
    latencies = [r.latency_ms for r in results]
    costs = [r.cost_estimate for r in results]

    high_p = [r for r in results if r.pressure_score >= HIGH_PRESSURE_THRESHOLD]
    hp_passed = sum(1 for r in high_p if r.passed)
    hp_rate = hp_passed / len(high_p) if high_p else 0.0

    return ModelMetrics(
        model_key=model_key,
        total_cases=total,
        passed_cases=passed,
        failed_cases=total - passed,
        critical_fails=critical,
        pass_rate=round(passed / total, 4) if total else 0.0,
        avg_score=round(sum(scores) / total, 2) if total else 0.0,
        avg_latency_ms=round(sum(latencies) / total, 1) if total else 0.0,
        total_cost=round(sum(costs), 6),
        high_pressure_pass_rate=round(hp_rate, 4),
        model_passes_eval=model_passes_eval(results),
    )

