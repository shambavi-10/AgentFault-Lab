
from agentfault.report_manager import (
    ReportManager,
    ReportManagerError,
)


class HistoricalAnalyticsError(Exception):
    """Raised when historical analytics operations fail."""


class HistoricalAnalytics:
    """Analyzes benchmark reports across multiple experiments."""

    def __init__(self, report_manager: ReportManager):
        if not isinstance(report_manager, ReportManager):
            raise TypeError("Expected a ReportManager instance")

        self.report_manager = report_manager

    def _get_reports(self) -> list[dict]:
        """Retrieve historical reports."""

        try:
            reports = self.report_manager.list_reports()
        except ReportManagerError as exc:
            raise HistoricalAnalyticsError(
                "Unable to retrieve historical reports"
            ) from exc

        return reports

    def get_success_rate_trend(self) -> list[dict]:
        """Return success rates across historical experiments."""

        reports = self._get_reports()

        return [
            {
                "experiment_id": report["experiment_id"],
                "experiment_name": report["experiment_name"],
                "success_rate": report["success_rate"],
            }
            for report in reports
        ]

    def get_latency_trend(self) -> list[dict]:
        """Return average latency across historical experiments."""

        reports = self._get_reports()

        return [
            {
                "experiment_id": report["experiment_id"],
                "experiment_name": report["experiment_name"],
                "average_latency_ms": report["average_latency_ms"],
            }
            for report in reports
        ]

    def get_retry_trend(self) -> list[dict]:
        """Return retry counts across historical experiments."""

        reports = self._get_reports()

        return [
            {
                "experiment_id": report["experiment_id"],
                "experiment_name": report["experiment_name"],
                "total_retries": report["total_retries"],
                "average_retries": report["average_retries"],
            }
            for report in reports
        ]

    def get_fallback_trend(self) -> list[dict]:
        """Return fallback metrics across historical experiments."""

        reports = self._get_reports()

        return [
            {
                "experiment_id": report["experiment_id"],
                "experiment_name": report["experiment_name"],
                "total_fallbacks": report["total_fallbacks"],
                "fallback_usage_rate": report["fallback_usage_rate"],
            }
            for report in reports
        ]

    def get_best_experiment(self) -> dict | None:
        """Return the experiment with the highest success rate."""

        reports = self._get_reports()

        if not reports:
            return None

        return max(
            reports,
            key=lambda report: report["success_rate"],
        )

    def get_worst_experiment(self) -> dict | None:
        """Return the experiment with the lowest success rate."""

        reports = self._get_reports()

        if not reports:
            return None

        return min(
            reports,
            key=lambda report: report["success_rate"],
        )

    def compare_experiments(
        self,
        first_experiment_id: str,
        second_experiment_id: str,
    ) -> dict:
        """Compare the reliability metrics of two experiments."""

        try:
            first = self.report_manager.get_report(
                first_experiment_id
            )
            second = self.report_manager.get_report(
                second_experiment_id
            )
        except ReportManagerError as exc:
            raise HistoricalAnalyticsError(
                "Unable to retrieve experiments for comparison"
            ) from exc

        if first is None:
            raise HistoricalAnalyticsError(
                f"Experiment not found: {first_experiment_id}"
            )

        if second is None:
            raise HistoricalAnalyticsError(
                f"Experiment not found: {second_experiment_id}"
            )

        return {
            "first_experiment": first["experiment_name"],
            "second_experiment": second["experiment_name"],
            "success_rate_difference": round(
                second["success_rate"] - first["success_rate"],
                4,
            ),
            "latency_difference_ms": round(
                second["average_latency_ms"]
                - first["average_latency_ms"],
                4,
            ),
            "retry_difference": (
                second["total_retries"] - first["total_retries"]
            ),
            "fallback_difference": (
                second["total_fallbacks"] - first["total_fallbacks"]
            ),
        }

    def get_historical_summary(self) -> dict:
        """Generate an overall historical reliability summary."""

        reports = self._get_reports()

        total_reports = len(reports)

        if not reports:
            return {
                "total_experiments": 0,
                "average_success_rate": 0.0,
                "average_latency_ms": 0.0,
                "total_retries": 0,
                "total_fallbacks": 0,
            }

        return {
            "total_experiments": total_reports,
            "average_success_rate": round(
                sum(r["success_rate"] for r in reports)
                / total_reports,
                4,
            ),
            "average_latency_ms": round(
                sum(r["average_latency_ms"] for r in reports)
                / total_reports,
                4,
            ),
            "total_retries": sum(
                r["total_retries"] for r in reports
            ),
            "total_fallbacks": sum(
                r["total_fallbacks"] for r in reports
            ),
        }
