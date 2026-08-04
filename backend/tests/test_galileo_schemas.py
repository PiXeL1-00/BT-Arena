from uuid import uuid4

from app.api.galileo_schemas import (
    DistributionItem,
    DistributionResponse,
    HeatmapCell,
    HeatmapResponse,
    ModelSummaryItem,
    ModelsSummaryResponse,
    ModelTrendSeries,
    ParetoItem,
    ParetoResponse,
    SweepTriggerResponse,
    TrendBucket,
    TrendResponse,
    UpliftItem,
    UpliftResponse,
)


class TestModelSummaryItem:
    def test_nullable_scores(self):
        item = ModelSummaryItem(
            llm_id=uuid4(), provider="openai", model_name="gpt-4o",
            display_name="OpenAI GPT-4o", is_active=True,
        )
        assert item.all_time_avg is None
        assert item.window_avg is None
        assert item.last_run_at is None
        assert item.all_time_runs == 0

    def test_with_scores(self):
        item = ModelSummaryItem(
            llm_id=uuid4(), provider="openai", model_name="gpt-4o",
            display_name="OpenAI GPT-4o", is_active=True,
            all_time_avg=85.5, all_time_runs=42,
            window_avg=88.0, window_runs=10,
        )
        assert item.all_time_avg == 85.5
        assert item.all_time_runs == 42

    def test_serialization_preserves_none(self):
        item = ModelSummaryItem(
            llm_id=uuid4(), provider="openai", model_name="gpt-4o",
            display_name="GPT-4o", is_active=True,
        )
        d = item.model_dump()
        assert d["all_time_avg"] is None
        assert d["window_avg"] is None


class TestModelsSummaryResponse:
    def test_empty_models_valid(self):
        resp = ModelsSummaryResponse(models=[], window_days=30, include_scheduled=False)
        assert resp.models == []

    def test_with_models(self):
        item = ModelSummaryItem(
            llm_id=uuid4(), provider="openai", model_name="gpt-4o",
            display_name="GPT-4o", is_active=True,
        )
        resp = ModelsSummaryResponse(models=[item], window_days=30, include_scheduled=True)
        assert len(resp.models) == 1
        assert resp.include_scheduled is True


class TestTrendResponse:
    def test_empty_series(self):
        resp = TrendResponse(series=[], window_days=30)
        assert resp.series == []

    def test_bucket_nullable_avg(self):
        bucket = TrendBucket(bucket="2025-01-01T00:00:00")
        assert bucket.score_avg is None
        assert bucket.n == 0


class TestDistributionResponse:
    def test_all_percentiles_nullable(self):
        item = DistributionItem(llm_id=uuid4())
        assert item.mean is None
        assert item.p10 is None
        assert item.p25 is None
        assert item.p50 is None
        assert item.p75 is None
        assert item.p90 is None

    def test_roundtrip(self):
        uid = uuid4()
        item = DistributionItem(
            llm_id=uid, mean=80.0, stddev=5.5, n=100,
            p10=70.0, p25=75.0, p50=80.0, p75=85.0, p90=92.0,
        )
        resp = DistributionResponse(items=[item])
        d = resp.model_dump()
        rebuilt = DistributionResponse.model_validate(d)
        assert rebuilt.items[0].mean == 80.0
        assert rebuilt.items[0].p90 == 92.0


class TestHeatmapResponse:
    def test_required_dataset_id(self):
        cell = HeatmapCell(llm_id=uuid4(), case_id="c1", avg_score=90.0, n=3)
        resp = HeatmapResponse(cells=[cell], dataset_id="ds1", top_k=50)
        assert resp.dataset_id == "ds1"
        assert resp.cells[0].avg_score == 90.0


class TestUpliftResponse:
    def test_delta_nullable(self):
        item = UpliftItem(llm_id=uuid4())
        assert item.delta is None
        assert item.avg_baseline is None
        assert item.avg_galileo is None
        assert item.n_pairs == 0


class TestParetoResponse:
    def test_nullable_cost(self):
        item = ParetoItem(llm_id=uuid4(), avg_score=85.0, n=5)
        assert item.avg_cost_usd is None
        assert item.avg_latency_ms is None


class TestSweepTriggerResponse:
    def test_defaults(self):
        resp = SweepTriggerResponse(status="ok")
        assert resp.models_swept == 0
        assert resp.evals_run == 0
        assert resp.message == ""

    def test_with_values(self):
        resp = SweepTriggerResponse(
            status="ok", models_swept=3, evals_run=15, message="Done",
        )
        assert resp.models_swept == 3
