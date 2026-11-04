
from agentfault.report_storage import (
    ReportStorage,
    ReportStorageError,
)


class ReportManagerError(Exception):
    """Raised when report management operations fail."""


class ReportManager:
    """Provides higher-level management of benchmark reports."""

    def __init__(self, storage: ReportStorage):
        if not isinstance(storage, ReportStorage):
            raise TypeError("Expected a ReportStorage instance")

        self.storage = storage

    def get_report(self, experiment_id: str) -> dict | None:
        """Retrieve a report using its experiment ID."""

        try:
            return self.storage.get_report(experiment_id)
        except (ReportStorageError, ValueError) as exc:
            raise ReportManagerError(
                f"Unable to retrieve report: {experiment_id}"
            ) from exc

    def list_reports(self) -> list[dict]:
        """Retrieve all saved reports."""

        try:
            return self.storage.list_reports()
        except ReportStorageError as exc:
            raise ReportManagerError(
                "Unable to list reports"
            ) from exc

    def filter_reports(
        self,
        experiment_status: str,
    ) -> list[dict]:
        """Return reports matching an experiment status."""

        if not experiment_status or not experiment_status.strip():
            raise ValueError("Experiment status cannot be empty")

        reports = self.list_reports()

        return [
            report
            for report in reports
            if report.get("experiment_status") == experiment_status
        ]

    def get_summary(self) -> dict:
        """Generate summary statistics for stored reports."""

        reports = self.list_reports()

        total_reports = len(reports)

        completed_reports = sum(
            1
            for report in reports
            if report.get("experiment_status") == "completed"
        )

        failed_reports = sum(
            1
            for report in reports
            if report.get("experiment_status") == "failed"
        )

        total_scenarios = sum(
            report.get("total_scenarios", 0)
            for report in reports
        )

        passed_scenarios = sum(
            report.get("passed_scenarios", 0)
            for report in reports
        )

        failed_scenarios = sum(
            report.get("failed_scenarios", 0)
            for report in reports
        )

        average_success_rate = (
            sum(report.get("success_rate", 0) for report in reports)
            / total_reports
            if total_reports
            else 0.0
        )

        return {
            "total_reports": total_reports,
            "completed_reports": completed_reports,
            "failed_reports": failed_reports,
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "failed_scenarios": failed_scenarios,
            "average_success_rate": average_success_rate,
        }

    def delete_report(self, experiment_id: str) -> bool:
        """Delete a report using its experiment ID."""

        try:
            return self.storage.delete_report(experiment_id)
        except (ReportStorageError, ValueError) as exc:
            raise ReportManagerError(
                f"Unable to delete report: {experiment_id}"
            ) from exc
