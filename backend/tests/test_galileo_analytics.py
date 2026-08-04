import pytest

from app.core.domain.schemas import BENCHMARK_TAG_AUTO_SWEEP
from app.usecases.freshness_sweep import (
    build_idempotency_key,
    select_deterministic_cases,
)


def _pool(pairs: list[tuple[str, str]]) -> list[dict]:
    return [{"dataset_id": ds, "case_id": cid} for ds, cid in pairs]


class TestSelectDeterministicCases:
    def test_returns_all_when_pool_small(self):
        pool = _pool([("ds1", "c1"), ("ds1", "c2")])
        result = select_deterministic_cases("2025-01-01", pool, n=5)
        assert len(result) == 2

    def test_returns_n_when_pool_large(self):
        pool = _pool([(f"ds{i}", f"c{j}") for i in range(5) for j in range(10)])
        result = select_deterministic_cases("2025-01-01", pool, n=5)
        assert len(result) == 5

    def test_deterministic_same_seed(self):
        pool = _pool([(f"ds{i}", f"c{j}") for i in range(3) for j in range(20)])
        r1 = select_deterministic_cases("2025-06-15", pool, n=5)
        r2 = select_deterministic_cases("2025-06-15", pool, n=5)
        assert r1 == r2

    def test_different_seed_different_selection(self):
        pool = _pool([(f"ds{i}", f"c{j}") for i in range(3) for j in range(20)])
        r1 = select_deterministic_cases("2025-01-01", pool, n=5)
        r2 = select_deterministic_cases("2025-01-02", pool, n=5)
        assert r1 != r2

    def test_stratified_across_datasets(self):
        pool = _pool([
            ("ds1", "c1"), ("ds1", "c2"), ("ds1", "c3"),
            ("ds2", "c4"), ("ds2", "c5"), ("ds2", "c6"),
        ])
        result = select_deterministic_cases("2025-01-01", pool, n=4)
        ds_ids = {item["dataset_id"] for item in result}
        assert len(ds_ids) == 2

    def test_empty_pool(self):
        result = select_deterministic_cases("2025-01-01", [], n=5)
        assert result == []

    def test_single_item(self):
        pool = _pool([("ds1", "c1")])
        result = select_deterministic_cases("2025-01-01", pool, n=5)
        assert len(result) == 1


class TestBuildIdempotencyKey:
    def test_format(self):
        key = build_idempotency_key(
            date="2025-01-15",
            llm_id="abc-123",
            eval_mode="galileo",
            dataset_id="ds1",
            case_id="c42",
        )
        assert key.startswith(BENCHMARK_TAG_AUTO_SWEEP)
        assert "2025-01-15" in key
        assert "abc-123" in key
        assert "galileo" in key
        assert "ds1" in key
        assert "c42" in key

    def test_deterministic(self):
        args = dict(
            date="2025-01-15", llm_id="x",
            eval_mode="galileo", dataset_id="ds1", case_id="c1",
        )
        assert build_idempotency_key(**args) == build_idempotency_key(**args)

    def test_different_dates_different_keys(self):
        base = dict(
            llm_id="x", eval_mode="galileo",
            dataset_id="ds1", case_id="c1",
        )
        k1 = build_idempotency_key(date="2025-01-01", **base)
        k2 = build_idempotency_key(date="2025-01-02", **base)
        assert k1 != k2


class TestBridgeHelpers:
    def test_extract_score_components_with_breakdown(self):
        from app.usecases.analytics_bridge import _extract_score_components
        from unittest.mock import MagicMock

        result = MagicMock()
        result.judge_json = {"score_breakdown": {"accuracy": 30, "evidence": 20}}
        assert _extract_score_components(result) == {"accuracy": 30, "evidence": 20}

    def test_extract_score_components_no_json(self):
        from app.usecases.analytics_bridge import _extract_score_components
        from unittest.mock import MagicMock

        result = MagicMock()
        result.judge_json = None
        assert _extract_score_components(result) is None

    def test_extract_score_components_no_breakdown(self):
        from app.usecases.analytics_bridge import _extract_score_components
        from unittest.mock import MagicMock

        result = MagicMock()
        result.judge_json = {"reasoning": "something"}
        assert _extract_score_components(result) is None

    def test_extract_failure_flags_present(self):
        from app.usecases.analytics_bridge import _extract_failure_flags
        from unittest.mock import MagicMock

        result = MagicMock()
        result.critical_fail_reason = "bad evidence"
        flags = _extract_failure_flags(result)
        assert flags == {"critical_fail": "bad evidence"}

    def test_extract_failure_flags_none(self):
        from app.usecases.analytics_bridge import _extract_failure_flags
        from unittest.mock import MagicMock

        result = MagicMock()
        result.critical_fail_reason = None
        assert _extract_failure_flags(result) is None
