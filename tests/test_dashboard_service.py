
import pytest

from agentfault.historical_analytics import HistoricalAnalytics
from agentfault.historical_insights import HistoricalInsights
from agentfault.recommendation_manager import RecommendationManager
from agentfault.report_manager import ReportManager
from agentfault.report_storage import ReportStorage
from agentfault.dashboard_service import (
    DashboardService,
    DashboardServiceError,
)


@pytest.fixture
def dashboard(tmp_path):
    storage = ReportStorage(tmp_path / "reports")
    report_manager = ReportManager(storage)

    analytics = HistoricalAnalytics(report_manager)
    insights = HistoricalInsights(analytics)

    recommendation_manager = RecommendationManager(
        tmp_path / "recommendations.json"
    )

    return DashboardService(
        analytics,
        insights,
        recommendation_manager,
    )


def test_dashboard_requires_valid_analytics(tmp_path):
    storage = ReportStorage(tmp_path / "reports")
    manager = RecommendationManager(tmp_path / "recommendations.json")

    analytics = HistoricalAnalytics(
        ReportManager(storage)
    )

    insights = HistoricalInsights(analytics)

    with pytest.raises(TypeError):
        DashboardService(
            "invalid",
            insights,
            manager,
        )


def test_dashboard_requires_valid_insights(tmp_path):
    storage = ReportStorage(tmp_path / "reports")
    analytics = HistoricalAnalytics(ReportManager(storage))
    manager = RecommendationManager(tmp_path / "recommendations.json")

    with pytest.raises(TypeError):
        DashboardService(
            analytics,
            "invalid",
            manager,
        )


def test_dashboard_requires_valid_recommendation_manager(tmp_path):
    storage = ReportStorage(tmp_path / "reports")
    analytics = HistoricalAnalytics(ReportManager(storage))
    insights = HistoricalInsights(analytics)

    with pytest.raises(TypeError):
        DashboardService(
            analytics,
            insights,
            "invalid",
        )


def test_insights_must_use_same_analytics_instance(tmp_path):
    storage = ReportStorage(tmp_path / "reports")

    analytics_one = HistoricalAnalytics(ReportManager(storage))
    analytics_two = HistoricalAnalytics(ReportManager(storage))

    insights = HistoricalInsights(analytics_two)
    recommendations = RecommendationManager(
        tmp_path / "recommendations.json"
    )

    with pytest.raises(ValueError):
        DashboardService(
            analytics_one,
            insights,
            recommendations,
        )


def test_empty_experiment_overview(dashboard):
    result = dashboard.get_experiment_overview()

    assert result["total_experiments"] == 0
    assert result["completed_experiments"] == 0
    assert result["failed_experiments"] == 0
    assert result["average_success_rate"] == 0.0


def test_empty_reliability_overview(dashboard):
    result = dashboard.get_reliability_overview()

    assert result["average_reliability_score"] == 0.0
    assert result["low_risk_experiments"] == 0
    assert result["medium_risk_experiments"] == 0
    assert result["high_risk_experiments"] == 0


def test_empty_recommendation_overview(dashboard):
    result = dashboard.get_recommendation_overview()

    assert result["total_recommendations"] == 0
    assert result["open"] == 0
    assert result["resolved"] == 0


def test_empty_performance_trends(dashboard):
    result = dashboard.get_performance_trends()

    assert result["success_rate"] == []
    assert result["latency"] == []
    assert result["retries"] == []
    assert result["fallbacks"] == []


def test_empty_experiment_highlights(dashboard):
    result = dashboard.get_experiment_highlights()

    assert result["best_experiment"] is None
    assert result["worst_experiment"] is None


def test_complete_dashboard_data(dashboard):
    result = dashboard.get_dashboard_data()

    assert "experiment_overview" in result
    assert "reliability_overview" in result
    assert "recommendation_overview" in result
    assert "performance_trends" in result
    assert "experiment_highlights" in result


def test_dashboard_overview_with_saved_reports(
    dashboard,
    tmp_path,
):
    from agentfault.benchmark_report import BenchmarkReport

    report = BenchmarkReport(
        experiment_id="exp-001",
        experiment_name="Dashboard Test",
        experiment_status="completed",
        total_scenarios=10,
        passed_scenarios=8,
        failed_scenarios=2,
        success_rate=0.8,
        failure_rate=0.2,
        average_latency_ms=100.0,
        minimum_latency_ms=50.0,
        maximum_latency_ms=150.0,
        p50_latency_ms=90.0,
        p90_latency_ms=140.0,
        p95_latency_ms=145.0,
        p99_latency_ms=149.0,
        total_retries=3,
        average_retries=0.3,
        total_fallbacks=1,
        fallback_usage_rate=0.1,
        scenario_reports=[],
    )

    dashboard.analytics.report_manager.storage.save_report(report)

    result = dashboard.get_experiment_overview()

    assert result["total_experiments"] == 1
    assert result["completed_experiments"] == 1
    assert result["average_success_rate"] == 0.8
    assert result["average_latency_ms"] == 100.0


def test_reliability_score_with_saved_report(dashboard):
    from agentfault.benchmark_report import BenchmarkReport

    report = BenchmarkReport(
        experiment_id="exp-002",
        experiment_name="Reliability Test",
        experiment_status="completed",
        total_scenarios=10,
        passed_scenarios=10,
        failed_scenarios=0,
        success_rate=1.0,
        failure_rate=0.0,
        average_latency_ms=100.0,
        minimum_latency_ms=50.0,
        maximum_latency_ms=150.0,
        p50_latency_ms=90.0,
        p90_latency_ms=140.0,
        p95_latency_ms=145.0,
        p99_latency_ms=149.0,
        total_retries=0,
        average_retries=0.0,
        total_fallbacks=0,
        fallback_usage_rate=0.0,
        scenario_reports=[],
    )

    dashboard.analytics.report_manager.storage.save_report(report)

    result = dashboard.get_reliability_overview()

    assert result["low_risk_experiments"] == 1
    assert result["average_reliability_score"] > 80


def test_dashboard_performance_trends_with_report(dashboard):
    from agentfault.benchmark_report import BenchmarkReport

    report = BenchmarkReport(
        experiment_id="exp-003",
        experiment_name="Trend Test",
        experiment_status="completed",
        total_scenarios=5,
        passed_scenarios=5,
        failed_scenarios=0,
        success_rate=1.0,
        failure_rate=0.0,
        average_latency_ms=120.0,
        minimum_latency_ms=100.0,
        maximum_latency_ms=150.0,
        p50_latency_ms=120.0,
        p90_latency_ms=140.0,
        p95_latency_ms=145.0,
        p99_latency_ms=149.0,
        total_retries=1,
        average_retries=0.2,
        total_fallbacks=0,
        fallback_usage_rate=0.0,
        scenario_reports=[],
    )

    dashboard.analytics.report_manager.storage.save_report(report)

    trends = dashboard.get_performance_trends()

    assert len(trends["success_rate"]) == 1
    assert len(trends["latency"]) == 1
    assert len(trends["retries"]) == 1
    assert len(trends["fallbacks"]) == 1


def test_experiment_highlights_with_saved_reports(dashboard):
    from agentfault.benchmark_report import BenchmarkReport

    reports = [
        BenchmarkReport(
            experiment_id="best",
            experiment_name="Best Experiment",
            experiment_status="completed",
            total_scenarios=10,
            passed_scenarios=10,
            failed_scenarios=0,
            success_rate=1.0,
            failure_rate=0.0,
            average_latency_ms=100.0,
            minimum_latency_ms=50.0,
            maximum_latency_ms=150.0,
            p50_latency_ms=90.0,
            p90_latency_ms=140.0,
            p95_latency_ms=145.0,
            p99_latency_ms=149.0,
            total_retries=0,
            average_retries=0.0,
            total_fallbacks=0,
            fallback_usage_rate=0.0,
            scenario_reports=[],
        ),
        BenchmarkReport(
            experiment_id="worst",
            experiment_name="Worst Experiment",
            experiment_status="failed",
            total_scenarios=10,
            passed_scenarios=3,
            failed_scenarios=7,
            success_rate=0.3,
            failure_rate=0.7,
            average_latency_ms=500.0,
            minimum_latency_ms=300.0,
            maximum_latency_ms=700.0,
            p50_latency_ms=450.0,
            p90_latency_ms=650.0,
            p95_latency_ms=675.0,
            p99_latency_ms=695.0,
            total_retries=5,
            average_retries=0.5,
            total_fallbacks=2,
            fallback_usage_rate=0.2,
            scenario_reports=[],
        ),
    ]

    for report in reports:
        dashboard.analytics.report_manager.storage.save_report(report)

    result = dashboard.get_experiment_highlights()

    assert result["best_experiment"]["experiment_id"] == "best"
    assert result["worst_experiment"]["experiment_id"] == "worst"


def test_dashboard_recommendation_summary_with_data(
    dashboard,
):
    from agentfault.recommendation_engine import ReliabilityRecommendation

    recommendation = ReliabilityRecommendation(
        experiment_id="exp-004",
        experiment_name="Recommendation Test",
        category="success",
        priority="critical",
        title="Investigate failures",
        description="Several scenarios failed.",
        action="Inspect execution traces.",
    )

    dashboard.recommendation_manager.add_recommendations(
        [recommendation]
    )

    result = dashboard.get_recommendation_overview()

    assert result["total_recommendations"] == 1
    assert result["open"] == 1
    assert result["priority_counts"]["critical"] == 1


def test_dashboard_data_contains_expected_sections(dashboard):
    result = dashboard.get_dashboard_data()

    assert set(result.keys()) == {
        "experiment_overview",
        "reliability_overview",
        "recommendation_overview",
        "performance_trends",
        "experiment_highlights",
    }
