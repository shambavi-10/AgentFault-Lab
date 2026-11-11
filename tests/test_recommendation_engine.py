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

from agentfault.recommendation_engine import (
    RecommendationEngine,
    RecommendationEngineError,
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
def engine(tmp_path):
    storage = ReportStorage(tmp_path / "reports")
    manager = ReportManager(storage)
    analytics = HistoricalAnalytics(manager)

    class TestReportManager:
        def __init__(self):
            self.reports = {}

        def get_report(self, experiment_id):
            return self.reports.get(experiment_id)

        def list_reports(self):
            return list(self.reports.values())

    stub = TestReportManager()
    analytics.report_manager = stub

    insights = HistoricalInsights(analytics)
    return RecommendationEngine(insights), stub


def test_constructor_requires_historical_insights():
    with pytest.raises(TypeError):
        RecommendationEngine("invalid")


def test_constructor_rejects_invalid_thresholds(engine):
    recommendation_engine, _ = engine

    with pytest.raises(ValueError):
        RecommendationEngine(
            recommendation_engine.insights,
            target_latency_ms=0,
        )

    with pytest.raises(ValueError):
        RecommendationEngine(
            recommendation_engine.insights,
            max_average_retries=0,
        )

    with pytest.raises(ValueError):
        RecommendationEngine(
            recommendation_engine.insights,
            max_fallback_usage_rate=0,
        )


def test_critical_success_recommendation(engine):
    recommendation_engine, manager = engine

    manager.reports["exp-001"] = create_report(
        "exp-001", "Unstable Agent", 0.4, 100, 0, 0
    )

    results = recommendation_engine.generate_recommendations("exp-001")

    assert results[0].priority == "critical"
    assert results[0].category == "success"


def test_high_success_recommendation(engine):
    recommendation_engine, manager = engine

    manager.reports["exp-002"] = create_report(
        "exp-002", "Weak Agent", 0.7, 100, 0, 0
    )

    results = recommendation_engine.generate_recommendations("exp-002")

    assert results[0].priority == "high"
    assert results[0].category == "success"


def test_latency_recommendation(engine):
    recommendation_engine, manager = engine

    manager.reports["exp-003"] = create_report(
        "exp-003", "Slow Agent", 1.0, 1500, 0, 0
    )

    results = recommendation_engine.generate_recommendations("exp-003")

    assert any(item.category == "latency" for item in results)


def test_retry_recommendation(engine):
    recommendation_engine, manager = engine

    manager.reports["exp-004"] = create_report(
        "exp-004", "Retry Heavy Agent", 1.0, 100, 2, 0
    )

    results = recommendation_engine.generate_recommendations("exp-004")

    assert any(item.category == "retry" for item in results)


def test_fallback_recommendation(engine):
    recommendation_engine, manager = engine

    manager.reports["exp-005"] = create_report(
        "exp-005", "Fallback Heavy Agent", 1.0, 100, 0, 0.5
    )

    results = recommendation_engine.generate_recommendations("exp-005")

    assert any(item.category == "fallback" for item in results)


def test_circuit_breaker_recommendation(engine):
    recommendation_engine, manager = engine

    manager.reports["exp-006"] = create_report(
        "exp-006", "Unstable External Service", 0.4, 100, 2, 0
    )

    results = recommendation_engine.generate_recommendations("exp-006")

    assert any(
        item.category == "circuit_breaker"
        for item in results
    )


def test_recommendations_are_sorted_by_priority(engine):
    recommendation_engine, manager = engine

    manager.reports["exp-007"] = create_report(
        "exp-007", "Problematic Agent", 0.4, 1500, 2, 0.5
    )

    results = recommendation_engine.generate_recommendations("exp-007")

    priorities = [item.priority for item in results]

    assert priorities == sorted(
        priorities,
        key={"critical": 0, "high": 1, "medium": 2, "low": 3}.get,
    )


def test_healthy_experiment_gets_monitoring_recommendation(engine):
    recommendation_engine, manager = engine

    manager.reports["exp-008"] = create_report(
        "exp-008", "Healthy Agent", 1.0, 100, 0, 0
    )

    results = recommendation_engine.generate_recommendations("exp-008")

    assert len(results) == 1
    assert results[0].category == "general"
    assert results[0].priority == "low"


def test_missing_experiment_raises_error(engine):
    recommendation_engine, _ = engine

    with pytest.raises(RecommendationEngineError):
        recommendation_engine.generate_recommendations("missing")


def test_all_experiments_generate_recommendations(engine):
    recommendation_engine, manager = engine

    manager.reports["exp-009"] = create_report(
        "exp-009", "Agent A", 1.0, 100, 0, 0
    )
    manager.reports["exp-010"] = create_report(
        "exp-010", "Agent B", 0.4, 100, 2, 0
    )

    results = recommendation_engine.generate_all_recommendations()

    assert len(results) >= 2
    assert all(item.experiment_id in {"exp-009", "exp-010"} for item in results)


def test_empty_collection_returns_empty_recommendations(engine):
    recommendation_engine, _ = engine

    assert recommendation_engine.generate_all_recommendations() == []

def test_report_retrieval_exception_is_wrapped(engine, monkeypatch):
    recommendation_engine, manager = engine
    original_error = RuntimeError("Database unavailable")

    def mock_get_report(experiment_id):
        raise original_error

    monkeypatch.setattr(manager, "get_report", mock_get_report)

    with pytest.raises(
        RecommendationEngineError,
        match="Unable to retrieve experiment report",
    ) as exc_info:
        recommendation_engine.generate_recommendations("exp-001")

    assert exc_info.value.__cause__ is original_error


def test_historical_insights_error_is_wrapped(engine, monkeypatch):
    recommendation_engine, manager = engine
    manager.reports["exp-001"] = create_report(
        "exp-001", "Test Agent", 1.0, 100, 0, 0
    )

    original_error = HistoricalInsightsError("Analysis failed")

    def mock_analyze_experiment(experiment_id):
        raise original_error

    monkeypatch.setattr(
        recommendation_engine.insights,
        "analyze_experiment",
        mock_analyze_experiment,
    )

    with pytest.raises(
        RecommendationEngineError,
        match="Unable to analyze experiment reliability",
    ) as exc_info:
        recommendation_engine.generate_recommendations("exp-001")

    assert exc_info.value.__cause__ is original_error


def test_historical_analytics_error_is_wrapped(engine, monkeypatch):
    recommendation_engine, _ = engine
    original_error = HistoricalAnalyticsError("Report listing failed")

    def mock_get_reports():
        raise original_error

    monkeypatch.setattr(
        recommendation_engine.insights.analytics,
        "_get_reports",
        mock_get_reports,
    )

    with pytest.raises(
        RecommendationEngineError,
        match="Unable to retrieve historical experiments",
    ) as exc_info:
        recommendation_engine.generate_all_recommendations()

    assert exc_info.value.__cause__ is original_error