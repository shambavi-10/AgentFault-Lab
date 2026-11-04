import json
from pathlib import Path

from agentfault.benchmark_report import (
    BenchmarkReport,
    export_benchmark_report_json,
)


class ReportStorageError(Exception):
    """Raised when benchmark report storage operations fail."""


class ReportStorage:
    """Manages persistent storage of benchmark reports."""

    def __init__(self, storage_dir: str | Path = "reports"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _get_report_path(self, experiment_id: str) -> Path:
        """Return the file path for an experiment report."""

        if not experiment_id or not experiment_id.strip():
            raise ValueError("Experiment ID cannot be empty")

        if Path(experiment_id).name != experiment_id:
            raise ValueError("Invalid experiment ID")

        if experiment_id in {".", ".."}:
            raise ValueError("Invalid experiment ID")

        return self.storage_dir / f"{experiment_id}.json"

    def save_report(self, report: BenchmarkReport) -> Path:
        """Save a benchmark report as a JSON file."""

        if not isinstance(report, BenchmarkReport):
            raise TypeError("Expected a BenchmarkReport instance")

        report_path = self._get_report_path(report.experiment_id)

        report_data = export_benchmark_report_json(report)

        with report_path.open("w", encoding="utf-8") as file:
            json.dump(
                report_data,
                file,
                indent=4,
            )

        return report_path

    def get_report(self, experiment_id: str) -> dict | None:
        """Retrieve a saved report using its experiment ID."""

        report_path = self._get_report_path(experiment_id)

        if not report_path.exists():
            return None

        try:
            with report_path.open("r", encoding="utf-8") as file:
                return json.load(file)

        except json.JSONDecodeError as exc:
            raise ReportStorageError(
                f"Report file is corrupted: {experiment_id}"
            ) from exc

        except OSError as exc:
            raise ReportStorageError(
                f"Unable to read report: {experiment_id}"
            ) from exc

    def list_reports(self) -> list[dict]:
        """Return all saved benchmark reports."""

        reports = []

        for report_path in sorted(self.storage_dir.glob("*.json")):
            try:
                with report_path.open("r", encoding="utf-8") as file:
                    reports.append(json.load(file))

            except (json.JSONDecodeError, OSError) as exc:
                raise ReportStorageError(
                    f"Unable to load report: {report_path.name}"
                ) from exc

        return reports

    def delete_report(self, experiment_id: str) -> bool:
        """Delete a saved report."""

        report_path = self._get_report_path(experiment_id)

        if not report_path.exists():
            return False

        try:
            report_path.unlink()
        except OSError as exc:
            raise ReportStorageError(
                f"Unable to delete report: {experiment_id}"
            ) from exc

        return True