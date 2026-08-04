"""Run comparison usecase -- regression analysis between two evaluation runs.

Compares per-case score deltas, verdict changes, evidence overlap, and
pass/fail flips to detect regressions or improvements.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.schemas import PassFlipStatus, ScoringMode
from app.infra.db.repository import Repository


# --- schemas ---

class CaseComparison(BaseModel):
    case_id: str
    model_key: str
    score_a: int
    score_b: int
    score_delta: int
    verdict_a: str
    verdict_b: str
    verdict_changed: bool
    passed_a: bool
    passed_b: bool
    pass_flip: PassFlipStatus
    evidence_overlap: float = Field(ge=0.0, le=1.0)


class RunComparison(BaseModel):
    run_a_id: str
    run_b_id: str
    total_cases_compared: int
    regressions: int
    improvements: int
    unchanged: int
    avg_score_delta: float
    cases: list[CaseComparison]
    has_regression: bool
    scoring_mode_mismatch: bool = False


# --- helpers ---

def _evidence_jaccard(eids_a: list[str], eids_b: list[str]) -> float:
    set_a, set_b = set(eids_a), set(eids_b)
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def _pass_flip(passed_a: bool, passed_b: bool) -> PassFlipStatus:
    if passed_a and not passed_b:
        return PassFlipStatus.REGRESSION
    if not passed_a and passed_b:
        return PassFlipStatus.IMPROVEMENT
    return PassFlipStatus.NONE


# --- main comparison ---

async def compare_runs(
    session: AsyncSession,
    run_a_id: str,
    run_b_id: str,
    *,
    model_key: Optional[str] = None,
) -> RunComparison:
    """Compare results of two runs and flag regressions.

    Args:
        session: Async DB session.
        run_a_id: Baseline run id.
        run_b_id: Candidate run id.
        model_key: Optional filter for a specific model.

    Returns:
        RunComparison with per-case deltas and aggregate statistics.
    """
    repo = Repository(session)

    # Check scoring mode mismatch for auditability
    run_a = await repo.get_run(run_a_id)
    run_b = await repo.get_run(run_b_id)
    mode_a = run_a.scoring_mode if run_a else ScoringMode.DETERMINISTIC.value
    mode_b = run_b.scoring_mode if run_b else ScoringMode.DETERMINISTIC.value
    mode_mismatch = mode_a != mode_b

    results_a = await repo.get_run_results(run_a_id, model_key=model_key)
    results_b = await repo.get_run_results(run_b_id, model_key=model_key)

    # Index by (case_id, model_key) for O(1) lookup
    idx_a = {(r.case_id, r.model_key): r for r in results_a}
    idx_b = {(r.case_id, r.model_key): r for r in results_b}

    # Compare overlapping keys
    common_keys = sorted(set(idx_a.keys()) & set(idx_b.keys()))

    cases: list[CaseComparison] = []
    regressions = 0
    improvements = 0
    deltas: list[int] = []

    for key in common_keys:
        ra = idx_a[key]
        rb = idx_b[key]

        delta = rb.score - ra.score
        deltas.append(delta)
        flip = _pass_flip(ra.passed, rb.passed)

        if flip == PassFlipStatus.REGRESSION:
            regressions += 1
        elif flip == PassFlipStatus.IMPROVEMENT:
            improvements += 1

        eids_a = ra.evidence_used_json if isinstance(ra.evidence_used_json, list) else []
        eids_b = rb.evidence_used_json if isinstance(rb.evidence_used_json, list) else []

        cases.append(CaseComparison(
            case_id=key[0],
            model_key=key[1],
            score_a=ra.score,
            score_b=rb.score,
            score_delta=delta,
            verdict_a=ra.verdict,
            verdict_b=rb.verdict,
            verdict_changed=(ra.verdict != rb.verdict),
            passed_a=ra.passed,
            passed_b=rb.passed,
            pass_flip=flip,
            evidence_overlap=_evidence_jaccard(eids_a, eids_b),
        ))

    total = len(cases)
    avg_delta = sum(deltas) / total if total else 0.0

    return RunComparison(
        run_a_id=run_a_id,
        run_b_id=run_b_id,
        total_cases_compared=total,
        regressions=regressions,
        improvements=improvements,
        unchanged=total - regressions - improvements,
        avg_score_delta=round(avg_delta, 2),
        cases=cases,
        has_regression=(regressions > 0),
        scoring_mode_mismatch=mode_mismatch,
    )
