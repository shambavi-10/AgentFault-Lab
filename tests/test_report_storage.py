
import json

import pytest
from pathlib import Path

from agentfault.report_storage import (
    ReportStorage,
    ReportStorageError,
)
from agentfault.benchmark_report import (
    BenchmarkReport,
    ScenarioReport,
)


@pytest.fixture
def sample_report():
    return BenchmarkReport(
        experiment_id="experiment-001",
        experiment_name="Storage Test",
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


@pytest.fixture
def storage(tmp_path):
    return ReportStorage(storage_dir=tmp_path / "reports")


# INITIALIZATION TESTS

def test_storage_creates_directory(tmp_path):
    directory = tmp_path / "new_reports"

    ReportStorage(directory)

    assert directory.exists()
    assert directory.is_dir()


# SAVE TESTS

def test_save_report_creates_json_file(storage, sample_report):
    path = storage.save_report(sample_report)

    assert path.exists()
    assert path.name == "experiment-001.json"


def test_saved_report_contains_correct_data(storage, sample_report):
    path = storage.save_report(sample_report)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["experiment_id"] == "experiment-001"
    assert data["experiment_name"] == "Storage Test"
    assert data["success_rate"] == 1.0


def test_save_report_rejects_invalid_object(storage):
    with pytest.raises(TypeError):
        storage.save_report({"experiment_id": "invalid"})


# RETRIEVAL TESTS

def test_get_report_returns_saved_report(storage, sample_report):
    storage.save_report(sample_report)

    report = storage.get_report("experiment-001")

    assert report is not None
    assert report["experiment_name"] == "Storage Test"


def test_get_report_returns_none_for_missing_report(storage):
    report = storage.get_report("missing-experiment")

    assert report is None


def test_get_report_preserves_scenario_details(storage, sample_report):
    storage.save_report(sample_report)

    report = storage.get_report("experiment-001")

    assert len(report["scenario_reports"]) == 2
    assert report["scenario_reports"][0]["scenario_name"] == "Scenario A"


# LIST TESTS

def test_list_reports_returns_all_saved_reports(storage, sample_report):
    storage.save_report(sample_report)

    reports = storage.list_reports()

    assert len(reports) == 1
    assert reports[0]["experiment_id"] == "experiment-001"


def test_list_reports_returns_empty_list(storage):
    assert storage.list_reports() == []


# DELETE TESTS

def test_delete_report_removes_file(storage, sample_report):
    storage.save_report(sample_report)

    deleted = storage.delete_report("experiment-001")

    assert deleted is True
    assert storage.get_report("experiment-001") is None


def test_delete_missing_report_returns_false(storage):
    deleted = storage.delete_report("missing-experiment")

    assert deleted is False


# VALIDATION TESTS

@pytest.mark.parametrize(
    "experiment_id",
    ["", "   ", "../outside", "folder/report", ".", ".."],
)
def test_invalid_experiment_ids_are_rejected(storage, experiment_id):
    with pytest.raises(ValueError):
        storage.get_report(experiment_id)


# PERSISTENCE TESTS

def test_report_persists_across_storage_instances(
    tmp_path,
    sample_report,
):
    directory = tmp_path / "persistent_reports"

    first_storage = ReportStorage(directory)
    first_storage.save_report(sample_report)

    second_storage = ReportStorage(directory)
    retrieved = second_storage.get_report("experiment-001")

    assert retrieved is not None
    assert retrieved["experiment_name"] == "Storage Test"


def test_multiple_reports_can_be_stored(storage, sample_report):
    storage.save_report(sample_report)

    second_report = BenchmarkReport(
        **{
            **sample_report.__dict__,
            "experiment_id": "experiment-002",
            "experiment_name": "Second Experiment",
        }
    )

    storage.save_report(second_report)

    reports = storage.list_reports()

    assert len(reports) == 2


# ERROR HANDLING TESTS

def test_corrupted_json_raises_storage_error(storage):
    corrupted_file = storage.storage_dir / "corrupted.json"

    corrupted_file.write_text(
        "{invalid json",
        encoding="utf-8",
    )

    with pytest.raises(ReportStorageError, match="corrupted"):
        storage.get_report("corrupted")

def test_get_report_raises_storage_error_on_read_failure(
    storage,
    monkeypatch,
):
    report_file = storage.storage_dir / "unreadable.json"
    report_file.write_text("{}", encoding="utf-8")

    original_open = Path.open

    def mock_open(self, *args, **kwargs):
        if self == report_file:
            raise PermissionError("Permission denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", mock_open)

    with pytest.raises(ReportStorageError, match="Unable to read report"):
        storage.get_report("unreadable")


def test_list_reports_raises_storage_error_on_corrupted_json(storage):
    corrupted_file = storage.storage_dir / "corrupted-list.json"
    corrupted_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(
        ReportStorageError,
        match="Unable to load report",
    ):
        storage.list_reports()


def test_delete_report_raises_storage_error_on_unlink_failure(
    storage,
    sample_report,
    monkeypatch,
):
    report_file = storage.save_report(sample_report)

    def mock_unlink(self, *args, **kwargs):
        if self == report_file:
            raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    with pytest.raises(
        ReportStorageError,
        match="Unable to delete report",
    ):
        storage.delete_report("experiment-001")