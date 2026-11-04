
from dataclasses import dataclass

from agentfault.historical_analytics import (
    HistoricalAnalytics,
    HistoricalAnalyticsError,
)


class HistoricalInsightsError(Exception):
    """Raised when historical insight generation fails."""


@dataclass
class ReliabilityInsights:
    """Stores reliability score and recommendations for an experiment."""

    experiment_id: str
    experiment_name: str

    reliability_score: float
    risk_level: str

    success_score: float
    latency_score: float
    retry_score: float
    fallback_score: float

    issues: list[str]
    recommendations: list[str]


class HistoricalInsights:
    """Generates actionable reliability insights from saved experiments."""

    def __init__(
        self,
        analytics: HistoricalAnalytics,
        target_latency_ms: float = 1000.0,
        max_average_retries: float = 1.0,
        max_fallback_usage_rate: float = 0.2,
    ):
        if not isinstance(analytics, HistoricalAnalytics):
            raise TypeError("Expected a HistoricalAnalytics instance")

        if target_latency_ms <= 0:
            raise ValueError("Target latency must be greater than zero")

        if max_average_retries <= 0:
            raise ValueError("Maximum average retries must be greater than zero")

        if not 0 < max_fallback_usage_rate <= 1:
            raise ValueError("Fallback usage threshold must be between 0 and 1")

        self.analytics = analytics
        self.target_latency_ms = target_latency_ms
        self.max_average_retries = max_average_retries
        self.max_fallback_usage_rate = max_fallback_usage_rate

    @staticmethod
    def _calculate_efficiency_score(
        actual: float,
        threshold: float,
        weight: float,
    ) -> float:
        """Calculate a score that decreases as usage exceeds its threshold."""

        if actual <= threshold:
            return weight

        return round(
            max(0.0, weight * (2 - actual / threshold)),
            2,
        )

    def analyze_experiment(
        self,
        experiment_id: str,
    ) -> ReliabilityInsights:
        """Calculate reliability score and recommendations."""

        try:
            report = self.analytics.report_manager.get_report(
                experiment_id
            )
        except HistoricalAnalyticsError as exc:
            raise HistoricalInsightsError(
                "Unable to retrieve experiment report"
            ) from exc
        except Exception as exc:
            raise HistoricalInsightsError(
                "Unable to retrieve experiment report"
            ) from exc

        if report is None:
            raise HistoricalInsightsError(
                f"Experiment not found: {experiment_id}"
            )

        try:
            success_rate = float(report["success_rate"])
            average_latency = float(report["average_latency_ms"])
            average_retries = float(report["average_retries"])
            fallback_usage_rate = float(report["fallback_usage_rate"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HistoricalInsightsError(
                "Experiment report contains invalid or missing metrics"
            ) from exc

        metrics = [
            success_rate,
            average_latency,
            average_retries,
            fallback_usage_rate,
        ]

        from math import isfinite

        if any(not isfinite(value) for value in metrics):
            raise HistoricalInsightsError(
                "Experiment metrics must contain finite numbers"
            )

        if not 0 <= success_rate <= 1:
            raise HistoricalInsightsError("Invalid success rate")

        if average_latency < 0 or average_retries < 0:
            raise HistoricalInsightsError("Latency and retries cannot be negative")

        if not 0 <= fallback_usage_rate <= 1:
            raise HistoricalInsightsError("Invalid fallback usage rate")

        success_score = round(success_rate * 50, 2)

        latency_score = round(
            max(
                0.0,
                20 * (1 - average_latency / self.target_latency_ms),
            ),
            2,
        )

        retry_score = self._calculate_efficiency_score(
            average_retries,
            self.max_average_retries,
            15,
        )

        fallback_score = self._calculate_efficiency_score(
            fallback_usage_rate,
            self.max_fallback_usage_rate,
            15,
        )

        reliability_score = round(
            success_score
            + latency_score
            + retry_score
            + fallback_score,
            2,
        )

        if reliability_score >= 80:
            risk_level = "low"
        elif reliability_score >= 60:
            risk_level = "medium"
        else:
            risk_level = "high"

        issues = []
        recommendations = []

        if success_rate < 0.8:
            issues.append("Low scenario success rate")
            recommendations.append(
                "Investigate failed scenarios and identify recurring failure causes."
            )

        if average_latency > self.target_latency_ms:
            issues.append("High average execution latency")
            recommendations.append(
                "Investigate slow tools, network delays, and unnecessary processing."
            )

        if average_retries > self.max_average_retries:
            issues.append("High retry usage")
            recommendations.append(
                "Review retry policies and investigate frequently failing operations."
            )

        if fallback_usage_rate > self.max_fallback_usage_rate:
            issues.append("High fallback usage")
            recommendations.append(
                "Investigate primary tool failures and improve primary execution reliability."
            )

        if not issues:
            recommendations.append(
                "Reliability is within the configured thresholds. Continue monitoring."
            )

        return ReliabilityInsights(
            experiment_id=report["experiment_id"],
            experiment_name=report["experiment_name"],
            reliability_score=reliability_score,
            risk_level=risk_level,
            success_score=success_score,
            latency_score=latency_score,
            retry_score=retry_score,
            fallback_score=fallback_score,
            issues=issues,
            recommendations=recommendations,
        )

    def analyze_all_experiments(self) -> list[ReliabilityInsights]:
        """Generate reliability insights for every saved experiment."""

        try:
            reports = self.analytics._get_reports()
        except HistoricalAnalyticsError as exc:
            raise HistoricalInsightsError(
                "Unable to retrieve historical experiments"
            ) from exc

        return [
            self.analyze_experiment(report["experiment_id"])
            for report in reports
        ]
