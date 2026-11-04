
import pytest

from agentfault.report_manager import (
    ReportManager,
    ReportManagerError,
)
from agentfault.report_storage import (
    ReportStorage,
    ReportStorageError,
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
def sample_report():
    return BenchmarkReport(
        experiment_id="experiment-001",
        experiment_name="Experiment One",
        experiment_status="completed",
        total_scenarios=2,
        passed_scenarios=2,
        failed_scenarios=0,
        success_rate=1.0,
        failure_rate=0.0,
        average_latency_ms=15.0,
        minimum_latency_ms=10.0,
        maximum_latency_ms=20.0,
        p50_latency_ms=10.0,
        p90_latency_ms=20.0,
        p95_latency_ms=20.0,
        p99_latency_ms=20.0,
        total_retries=1,
        average_retries=0.5,
        total_fallbacks=0,
        fallback_usage_rate=0.0,
        scenario_reports=[
            ScenarioReport(
                scenario_name="Scenario A",
                expected_status="success",
                actual_status="success",
                passed=True,
                execution_time_ms=10.0,
                retry_count=0,
                fallback_count=0,
            ),
            ScenarioReport(
                scenario_name="Scenario B",
                expected_status="success",
                actual_status="success",
                passed=True,
                execution_time_ms=20.0,
                retry_count=1,
                fallback_count=0,
            ),
        ],
    )


def save_report_with_status(storage, sample_report, experiment_id, status):
    report = BenchmarkReport(
        **{
            **sample_report.__dict__,
            "experiment_id": experiment_id,
            "experiment_status": status,
        }
    )
    storage.save_report(report)


# INITIALIZATION TESTS

def test_manager_requires_report_storage():
    with pytest.raises(TypeError):
        ReportManager("invalid storage")


# RETRIEVAL TESTS

def test_get_report_returns_saved_report(
    manager,
    storage,
    sample_report,
):
    storage.save_report(sample_report)

    report = manager.get_report("experiment-001")

    assert report is not None
    assert report["experiment_name"] == "Experiment One"


def test_get_report_returns_none_when_missing(manager):
    assert manager.get_report("missing") is None


def test_get_report_wraps_storage_error(manager, storage):
    def raise_storage_error(experiment_id):
        raise ReportStorageError("Storage failed")

    storage.get_report = raise_storage_error

    with pytest.raises(ReportManagerError):
        manager.get_report("experiment-001")


def test_get_report_wraps_invalid_id(manager):
    with pytest.raises(ReportManagerError):
        manager.get_report("../invalid")


# LIST TESTS

def test_list_reports_returns_all_reports(
    manager,
    storage,
    sample_report,
):
    storage.save_report(sample_report)

    reports = manager.list_reports()

    assert len(reports) == 1
    assert reports[0]["experiment_id"] == "experiment-001"


def test_list_reports_returns_empty_list(manager):
    assert manager.list_reports() == []


def test_list_reports_wraps_storage_error(manager, storage):
    def raise_storage_error():
        raise ReportStorageError("Storage failed")

    storage.list_reports = raise_storage_error

    with pytest.raises(ReportManagerError):
        manager.list_reports()


# FILTER TESTS

def test_filter_reports_returns_matching_status(
    manager,
    storage,
    sample_report,
):
    save_report_with_status(
        storage,
        sample_report,
        "experiment-001",
        "completed",
    )

    save_report_with_status(
        storage,
        sample_report,
        "experiment-002",
        "failed",
    )

    completed = manager.filter_reports("completed")

    assert len(completed) == 1
    assert completed[0]["experiment_id"] == "experiment-001"


def test_filter_reports_returns_empty_list_for_no_match(
    manager,
    storage,
    sample_report,
):
    storage.save_report(sample_report)

    reports = manager.filter_reports("failed")

    assert reports == []


def test_filter_reports_rejects_empty_status(manager):
    with pytest.raises(ValueError):
        manager.filter_reports("")


# SUMMARY TESTS

def test_get_summary_returns_correct_statistics(
    manager,
    storage,
    sample_report,
):
    save_report_with_status(
        storage,
        sample_report,
        "experiment-001",
        "completed",
    )

    save_report_with_status(
        storage,
        sample_report,
        "experiment-002",
        "failed",
    )

    summary = manager.get_summary()

    assert summary["total_reports"] == 2
    assert summary["completed_reports"] == 1
    assert summary["failed_reports"] == 1
    assert summary["total_scenarios"] == 4
    assert summary["passed_scenarios"] == 4
    assert summary["failed_scenarios"] == 0
    assert summary["average_success_rate"] == 1.0


def test_get_summary_returns_zero_values_when_empty(manager):
    summary = manager.get_summary()

    assert summary["total_reports"] == 0
    assert summary["completed_reports"] == 0
    assert summary["failed_reports"] == 0
    assert summary["total_scenarios"] == 0
    assert summary["passed_scenarios"] == 0
    assert summary["failed_scenarios"] == 0
    assert summary["average_success_rate"] == 0.0


# DELETE TESTS

def test_delete_report_removes_report(
    manager,
    storage,
    sample_report,
):
    storage.save_report(sample_report)

    deleted = manager.delete_report("experiment-001")

    assert deleted is True
    assert manager.get_report("experiment-001") is None


def test_delete_missing_report_returns_false(manager):
    assert manager.delete_report("missing") is False


def test_delete_report_wraps_invalid_id(manager):
    with pytest.raises(ReportManagerError):
        manager.delete_report("../invalid")
