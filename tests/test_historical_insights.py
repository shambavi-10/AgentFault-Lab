
import pytest

from agentfault.report_storage import ReportStorage
from agentfault.report_manager import ReportManager
from agentfault.historical_analytics import (
    HistoricalAnalytics,
    HistoricalAnalyticsError,
)
from agentfault.historical_insights import (
    HistoricalInsights,
    HistoricalInsightsError,
)


def create_report(
    experiment_id,
    name,
    success_rate,
    latency,
    average_retries,
    fallback_usage_rate,
):
    return {
        "experiment_id": experiment_id,
        "experiment_name": name,
        "experiment_status": "completed",
        "total_scenarios": 10,
        "passed_scenarios": round(10 * success_rate),
        "failed_scenarios": 10 - round(10 * success_rate),
        "success_rate": success_rate,
        "average_latency_ms": latency,
        "average_retries": average_retries,
        "fallback_usage_rate": fallback_usage_rate,
    }


@pytest.fixture
def insights(tmp_path):
    storage = ReportStorage(tmp_path / "reports")
    manager = ReportManager(storage)
    analytics = HistoricalAnalytics(manager)

    # Use a lightweight report-manager stub so tests can
    # supply reports without depending on report serialization.
    class TestReportManager:
        def __init__(self):
            self.reports = {}

        def get_report(self, experiment_id):
            return self.reports.get(experiment_id)

        def list_reports(self):
            return list(self.reports.values())

    stub = TestReportManager()
    analytics.report_manager = stub

    engine = HistoricalInsights(analytics)
    return engine, stub


def test_constructor_requires_historical_analytics():
    with pytest.raises(TypeError):
        HistoricalInsights("invalid")


def test_constructor_rejects_invalid_thresholds(insights):
    engine, _ = insights

    with pytest.raises(ValueError):
        HistoricalInsights(engine.analytics, target_latency_ms=0)

    with pytest.raises(ValueError):
        HistoricalInsights(engine.analytics, max_average_retries=0)

    with pytest.raises(ValueError):
        HistoricalInsights(engine.analytics, max_fallback_usage_rate=0)


def test_perfect_experiment_gets_full_score(insights):
    engine, manager = insights

    manager.reports["exp-001"] = create_report(
        "exp-001", "Perfect Experiment", 1.0, 0, 0, 0
    )

    result = engine.analyze_experiment("exp-001")

    assert result.reliability_score == 100
    assert result.risk_level == "low"
    assert result.issues == []


def test_low_success_rate_generates_issue(insights):
    engine, manager = insights

    manager.reports["exp-002"] = create_report(
        "exp-002", "Unstable Experiment", 0.4, 100, 0, 0
    )

    result = engine.analyze_experiment("exp-002")

    assert result.success_score == 20
    assert "Low scenario success rate" in result.issues


def test_high_latency_generates_issue(insights):
    engine, manager = insights

    manager.reports["exp-003"] = create_report(
        "exp-003", "Slow Experiment", 1.0, 1500, 0, 0
    )

    result = engine.analyze_experiment("exp-003")

    assert "High average execution latency" in result.issues


def test_high_retry_usage_generates_issue(insights):
    engine, manager = insights

    manager.reports["exp-004"] = create_report(
        "exp-004", "Retry Heavy Experiment", 1.0, 100, 2, 0
    )

    result = engine.analyze_experiment("exp-004")

    assert "High retry usage" in result.issues


def test_high_fallback_usage_generates_issue(insights):
    engine, manager = insights

    manager.reports["exp-005"] = create_report(
        "exp-005", "Fallback Heavy Experiment", 1.0, 100, 0, 0.5
    )

    result = engine.analyze_experiment("exp-005")

    assert "High fallback usage" in result.issues


def test_missing_experiment_raises_error(insights):
    engine, _ = insights

    with pytest.raises(HistoricalInsightsError):
        engine.analyze_experiment("missing")


def test_all_experiments_are_analyzed(insights):
    engine, manager = insights

    manager.reports["exp-001"] = create_report(
        "exp-001", "Experiment A", 1.0, 100, 0, 0
    )
    manager.reports["exp-002"] = create_report(
        "exp-002", "Experiment B", 0.6, 200, 2, 0.4
    )

    results = engine.analyze_all_experiments()

    assert len(results) == 2
    assert results[0].experiment_name == "Experiment A"
    assert results[1].experiment_name == "Experiment B"


def test_empty_experiment_collection_returns_empty_list(insights):
    engine, _ = insights

    assert engine.analyze_all_experiments() == []


def test_invalid_success_rate_is_rejected(insights):
    engine, manager = insights

    manager.reports["exp-006"] = create_report(
        "exp-006", "Invalid Experiment", 1.5, 100, 0, 0
    )

    with pytest.raises(HistoricalInsightsError):
        engine.analyze_experiment("exp-006")


def test_recommendations_are_generated(insights):
    engine, manager = insights

    manager.reports["exp-007"] = create_report(
        "exp-007", "Problematic Experiment", 0.4, 1500, 2, 0.5
    )

    result = engine.analyze_experiment("exp-007")

    assert len(result.issues) == 4
    assert len(result.recommendations) == 4
    assert result.risk_level == "high"


def test_report_retrieval_historical_analytics_error(insights, monkeypatch):
    engine, manager = insights

    def fail_get_report(experiment_id):
        raise HistoricalAnalyticsError("Database error")

    monkeypatch.setattr(manager, "get_report", fail_get_report)

    with pytest.raises(HistoricalInsightsError):
        engine.analyze_experiment("exp-error")


def test_report_retrieval_unexpected_error(insights, monkeypatch):
    engine, manager = insights

    def fail_get_report(experiment_id):
        raise RuntimeError("Unexpected database failure")

    monkeypatch.setattr(manager, "get_report", fail_get_report)

    with pytest.raises(HistoricalInsightsError):
        engine.analyze_experiment("exp-error")


@pytest.mark.parametrize(
    "metric",
    ["success_rate", "average_latency_ms", "average_retries",
     "fallback_usage_rate"],
)
def test_non_finite_metrics_are_rejected(insights, metric):
    engine, manager = insights
    report = create_report("exp-nan", "Invalid Metrics", 1.0, 100, 0, 0)
    report[metric] = float("nan")
    manager.reports["exp-nan"] = report

    with pytest.raises(HistoricalInsightsError, match="finite numbers"):
        engine.analyze_experiment("exp-nan")


@pytest.mark.parametrize(
    "metric",
    ["success_rate", "average_latency_ms", "average_retries",
     "fallback_usage_rate"],
)
def test_infinite_metrics_are_rejected(insights, metric):
    engine, manager = insights
    report = create_report("exp-inf", "Infinite Metrics", 1.0, 100, 0, 0)
    report[metric] = float("inf")
    manager.reports["exp-inf"] = report

    with pytest.raises(HistoricalInsightsError, match="finite numbers"):
        engine.analyze_experiment("exp-inf")


@pytest.mark.parametrize(
    "metric",
    ["success_rate", "average_latency_ms", "average_retries",
     "fallback_usage_rate"],
)
def test_missing_metrics_are_rejected(insights, metric):
    engine, manager = insights
    report = create_report("exp-missing", "Missing Metrics", 1.0, 100, 0, 0)
    del report[metric]
    manager.reports["exp-missing"] = report

    with pytest.raises(HistoricalInsightsError, match="invalid or missing"):
        engine.analyze_experiment("exp-missing")


@pytest.mark.parametrize(
    "metric,value",
    [
        ("success_rate", "invalid"),
        ("average_latency_ms", None),
        ("average_retries", "invalid"),
        ("fallback_usage_rate", None),
    ],
)
def test_invalid_metric_types_are_rejected(insights, metric, value):
    engine, manager = insights
    report = create_report("exp-invalid", "Invalid Types", 1.0, 100, 0, 0)
    report[metric] = value
    manager.reports["exp-invalid"] = report

    with pytest.raises(HistoricalInsightsError):
        engine.analyze_experiment("exp-invalid")


@pytest.mark.parametrize(
    "metric,value",
    [
        ("success_rate", -0.1),
        ("average_latency_ms", -1),
        ("average_retries", -1),
        ("fallback_usage_rate", -0.1),
        ("fallback_usage_rate", 1.1),
    ],
)
def test_out_of_range_metrics_are_rejected(insights, metric, value):
    engine, manager = insights
    report = create_report("exp-range", "Out of Range", 1.0, 100, 0, 0)
    report[metric] = value
    manager.reports["exp-range"] = report

    with pytest.raises(HistoricalInsightsError):
        engine.analyze_experiment("exp-range")


def test_analyze_all_experiments_wraps_analytics_error(insights, monkeypatch):
    engine, _ = insights

    def fail_get_reports():
        raise HistoricalAnalyticsError("Unable to read reports")

    monkeypatch.setattr(engine.analytics, "_get_reports", fail_get_reports)

    with pytest.raises(HistoricalInsightsError, match="Unable to retrieve"):
        engine.analyze_all_experiments()
