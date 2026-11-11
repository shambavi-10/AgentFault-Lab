
import pytest

from agentfault.report_storage import ReportStorage
from agentfault.report_manager import (
    ReportManager,
    ReportManagerError,
)
from agentfault.historical_analytics import (
    HistoricalAnalytics,
    HistoricalAnalyticsError,
)
from agentfault.benchmark_report import (
    BenchmarkReport,
    ScenarioReport,
)


@pytest.fixture
def storage(tmp_path):
    return ReportStorage(tmp_path / "reports")


@pytest.fixture
def manager(storage):
    return ReportManager(storage)


@pytest.fixture
def analytics(manager):
    return HistoricalAnalytics(manager)


def create_report(
    experiment_id,
    name,
    success_rate,
    latency,
    retries,
    fallbacks,
):
    total_scenarios = 10
    passed = round(total_scenarios * success_rate)

    return BenchmarkReport(
        experiment_id=experiment_id,
        experiment_name=name,
        experiment_status="completed",
        total_scenarios=total_scenarios,
        passed_scenarios=passed,
        failed_scenarios=total_scenarios - passed,
        success_rate=success_rate,
        failure_rate=1 - success_rate,
        average_latency_ms=latency,
        minimum_latency_ms=10.0,
        maximum_latency_ms=50.0,
        p50_latency_ms=20.0,
        p90_latency_ms=40.0,
        p95_latency_ms=45.0,
        p99_latency_ms=50.0,
        total_retries=retries,
        average_retries=retries / total_scenarios,
        total_fallbacks=fallbacks,
        fallback_usage_rate=fallbacks / total_scenarios,
        scenario_reports=[
            ScenarioReport(
                scenario_name=f"Scenario {index}",
                expected_status="success",
                actual_status="success",
                passed=True,
                execution_time_ms=20.0,
                retry_count=0,
                fallback_count=0,
            )
            for index in range(total_scenarios)
        ],
    )


@pytest.fixture
def populated_analytics(storage, manager):
    reports = [
        create_report("exp-001", "Experiment A", 1.0, 20, 2, 1),
        create_report("exp-002", "Experiment B", 0.6, 40, 5, 3),
        create_report("exp-003", "Experiment C", 0.8, 30, 3, 2),
    ]

    for report in reports:
        storage.save_report(report)

    return HistoricalAnalytics(manager)


# INITIALIZATION TESTS

def test_analytics_requires_report_manager():
    with pytest.raises(TypeError):
        HistoricalAnalytics("invalid")


# SUCCESS RATE TREND TESTS

def test_success_rate_trend(populated_analytics):
    trend = populated_analytics.get_success_rate_trend()

    assert len(trend) == 3
    assert trend[0]["success_rate"] == 1.0
    assert trend[1]["success_rate"] == 0.6
    assert trend[2]["success_rate"] == 0.8


def test_success_rate_trend_empty(analytics):
    assert analytics.get_success_rate_trend() == []


# LATENCY TREND TESTS

def test_latency_trend(populated_analytics):
    trend = populated_analytics.get_latency_trend()

    assert len(trend) == 3
    assert trend[0]["average_latency_ms"] == 20
    assert trend[1]["average_latency_ms"] == 40


# RETRY TREND TESTS

def test_retry_trend(populated_analytics):
    trend = populated_analytics.get_retry_trend()

    assert trend[0]["total_retries"] == 2
    assert trend[1]["total_retries"] == 5
    assert trend[2]["average_retries"] == 0.3


# FALLBACK TREND TESTS

def test_fallback_trend(populated_analytics):
    trend = populated_analytics.get_fallback_trend()

    assert trend[0]["total_fallbacks"] == 1
    assert trend[1]["total_fallbacks"] == 3
    assert trend[2]["fallback_usage_rate"] == 0.2


# BEST AND WORST EXPERIMENT TESTS

def test_get_best_experiment(populated_analytics):
    best = populated_analytics.get_best_experiment()

    assert best["experiment_id"] == "exp-001"
    assert best["success_rate"] == 1.0


def test_get_worst_experiment(populated_analytics):
    worst = populated_analytics.get_worst_experiment()

    assert worst["experiment_id"] == "exp-002"
    assert worst["success_rate"] == 0.6


def test_best_experiment_returns_none_when_empty(analytics):
    assert analytics.get_best_experiment() is None


def test_worst_experiment_returns_none_when_empty(analytics):
    assert analytics.get_worst_experiment() is None


# EXPERIMENT COMPARISON TESTS

def test_compare_experiments(populated_analytics):
    comparison = populated_analytics.compare_experiments(
        "exp-001",
        "exp-002",
    )

    assert comparison["success_rate_difference"] == -0.4
    assert comparison["latency_difference_ms"] == 20
    assert comparison["retry_difference"] == 3
    assert comparison["fallback_difference"] == 2


def test_compare_missing_experiment(populated_analytics):
    with pytest.raises(HistoricalAnalyticsError):
        populated_analytics.compare_experiments(
            "exp-001",
            "missing",
        )


# HISTORICAL SUMMARY TESTS

def test_historical_summary(populated_analytics):
    summary = populated_analytics.get_historical_summary()

    assert summary["total_experiments"] == 3
    assert summary["average_success_rate"] == 0.8
    assert summary["average_latency_ms"] == 30
    assert summary["total_retries"] == 10
    assert summary["total_fallbacks"] == 6


def test_historical_summary_empty(analytics):
    summary = analytics.get_historical_summary()

    assert summary == {
        "total_experiments": 0,
        "average_success_rate": 0.0,
        "average_latency_ms": 0.0,
        "total_retries": 0,
        "total_fallbacks": 0,
    }


def test_get_reports_raises_historical_analytics_error(
    analytics,
    monkeypatch,
):
    original_error = ReportManagerError("Storage failure")

    def mock_list_reports():
        raise original_error

    monkeypatch.setattr(
        analytics.report_manager,
        "list_reports",
        mock_list_reports,
    )

    with pytest.raises(
        HistoricalAnalyticsError,
        match="Unable to retrieve historical reports",
    ) as exc_info:
        analytics.get_success_rate_trend()

    assert exc_info.value.__cause__ is original_error


def test_compare_experiments_handles_report_manager_error(
    analytics,
    monkeypatch,
):
    original_error = ReportManagerError("Report retrieval failure")

    def mock_get_report(experiment_id):
        raise original_error

    monkeypatch.setattr(
        analytics.report_manager,
        "get_report",
        mock_get_report,
    )

    with pytest.raises(
        HistoricalAnalyticsError,
        match="Unable to retrieve experiments for comparison",
    ) as exc_info:
        analytics.compare_experiments("exp-001", "exp-002")

    assert exc_info.value.__cause__ is original_error

def test_compare_experiments_when_first_experiment_is_missing(
    populated_analytics,
):
    with pytest.raises(
        HistoricalAnalyticsError,
        match="Experiment not found: missing",
    ):
        populated_analytics.compare_experiments(
            "missing",
            "exp-002",
        )