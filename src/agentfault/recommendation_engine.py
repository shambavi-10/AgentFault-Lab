
from dataclasses import dataclass

from agentfault.historical_insights import (
    HistoricalInsights,
    HistoricalInsightsError,
)


class RecommendationEngineError(Exception):
    """Raised when recommendation generation fails."""


@dataclass
class ReliabilityRecommendation:
    """Represents one actionable reliability recommendation."""

    experiment_id: str
    experiment_name: str
    category: str
    priority: str
    title: str
    description: str
    action: str


class RecommendationEngine:
    """Generates prioritized reliability improvement recommendations."""

    def __init__(
        self,
        insights: HistoricalInsights,
        target_latency_ms: float = 1000.0,
        max_average_retries: float = 1.0,
        max_fallback_usage_rate: float = 0.2,
    ):
        if not isinstance(insights, HistoricalInsights):
            raise TypeError("Expected a HistoricalInsights instance")

        if target_latency_ms <= 0:
            raise ValueError("Target latency must be greater than zero")

        if max_average_retries <= 0:
            raise ValueError("Maximum average retries must be greater than zero")

        if not 0 < max_fallback_usage_rate <= 1:
            raise ValueError("Fallback threshold must be between 0 and 1")

        self.insights = insights
        self.target_latency_ms = target_latency_ms
        self.max_average_retries = max_average_retries
        self.max_fallback_usage_rate = max_fallback_usage_rate

    def generate_recommendations(
        self,
        experiment_id: str,
    ) -> list[ReliabilityRecommendation]:
        """Generate recommendations for one experiment."""

        try:
            report = self.insights.analytics.report_manager.get_report(
                experiment_id
            )
        except Exception as exc:
            raise RecommendationEngineError(
                "Unable to retrieve experiment report"
            ) from exc

        if report is None:
            raise RecommendationEngineError(
                f"Experiment not found: {experiment_id}"
            )

        try:
            result = self.insights.analyze_experiment(experiment_id)
        except HistoricalInsightsError as exc:
            raise RecommendationEngineError(
                "Unable to analyze experiment reliability"
            ) from exc

        recommendations = []

        def add_recommendation(
            category,
            priority,
            title,
            description,
            action,
        ):
            recommendations.append(
                ReliabilityRecommendation(
                    experiment_id=experiment_id,
                    experiment_name=result.experiment_name,
                    category=category,
                    priority=priority,
                    title=title,
                    description=description,
                    action=action,
                )
            )

        success_rate = report["success_rate"]
        average_latency = report["average_latency_ms"]
        average_retries = report["average_retries"]
        fallback_usage_rate = report["fallback_usage_rate"]

        # Success-rate recommendations

        if success_rate < 0.5:
            add_recommendation(
                "success",
                "critical",
                "Investigate critical scenario failures",
                "Less than half of the experiment scenarios passed.",
                "Inspect failed execution traces, identify recurring errors, "
                "and correct the underlying failure causes.",
            )

        elif success_rate < 0.8:
            add_recommendation(
                "success",
                "high",
                "Improve scenario success rate",
                "A significant portion of experiment scenarios failed.",
                "Review failed scenarios and improve error handling "
                "and recovery behavior.",
            )

        # Latency recommendations

        if average_latency > self.target_latency_ms:
            add_recommendation(
                "latency",
                "high",
                "Optimize execution latency",
                "Average execution latency exceeds the configured target.",
                "Profile slow tool calls, inspect network delays, "
                "and remove unnecessary processing.",
            )

        # Retry recommendations

        if average_retries > self.max_average_retries:
            add_recommendation(
                "retry",
                "medium",
                "Optimize retry configuration",
                "Average retry usage exceeds the configured threshold.",
                "Review retry limits, exponential backoff, jitter, "
                "and retryable error classification.",
            )

        # Fallback recommendations

        if fallback_usage_rate > self.max_fallback_usage_rate:
            add_recommendation(
                "fallback",
                "medium",
                "Reduce fallback dependency",
                "Fallback usage exceeds the configured threshold.",
                "Investigate primary tool failures and improve "
                "the reliability of primary execution paths.",
            )

        # Circuit-breaker recommendations

        if success_rate < 0.5 and average_retries > self.max_average_retries:
            add_recommendation(
                "circuit_breaker",
                "high",
                "Consider circuit-breaker protection",
                "Low success rate combined with high retry usage "
                "may indicate repeated failures against an unreliable service.",
                "Evaluate a circuit breaker with an appropriate failure "
                "threshold, recovery timeout, and half-open probe.",
            )

        if not recommendations:
            add_recommendation(
                "general",
                "low",
                "Continue reliability monitoring",
                "No configured recommendation thresholds were exceeded.",
                "Continue running benchmark experiments and monitor "
                "success rate, latency, retries, and fallback usage.",
            )

        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        recommendations.sort(
            key=lambda item: priority_order[item.priority]
        )

        return recommendations

    def generate_all_recommendations(
        self,
    ) -> list[ReliabilityRecommendation]:
        """Generate recommendations for all saved experiments."""

        try:
            reports = self.insights.analytics._get_reports()
        except HistoricalAnalyticsError as exc:
            raise RecommendationEngineError(
                "Unable to retrieve historical experiments"
            ) from exc

        recommendations = []

        for report in reports:
            recommendations.extend(
                self.generate_recommendations(report["experiment_id"])
            )

        return recommendations
