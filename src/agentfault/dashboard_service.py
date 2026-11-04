
from agentfault.historical_analytics import (
    HistoricalAnalytics,
    HistoricalAnalyticsError,
)
from agentfault.historical_insights import (
    HistoricalInsights,
    HistoricalInsightsError,
)
from agentfault.recommendation_manager import (
    RecommendationManager,
    RecommendationManagerError,
)


class DashboardServiceError(Exception):
    """Raised when dashboard data aggregation fails."""


class DashboardService:
    """Aggregates reliability data for the AgentFault Lab dashboard."""

    def __init__(
        self,
        analytics: HistoricalAnalytics,
        insights: HistoricalInsights,
        recommendation_manager: RecommendationManager,
    ):
        if not isinstance(analytics, HistoricalAnalytics):
            raise TypeError(
                "Expected a HistoricalAnalytics instance"
            )

        if not isinstance(insights, HistoricalInsights):
            raise TypeError(
                "Expected a HistoricalInsights instance"
            )

        if not isinstance(
            recommendation_manager,
            RecommendationManager,
        ):
            raise TypeError(
                "Expected a RecommendationManager instance"
            )

        if insights.analytics is not analytics:
            raise ValueError(
                "HistoricalInsights must use the supplied analytics instance"
            )

        self.analytics = analytics
        self.insights = insights
        self.recommendation_manager = recommendation_manager

    def get_experiment_overview(self) -> dict:
        """Return overall experiment statistics."""

        try:
            reports = self.analytics.report_manager.list_reports()
            historical = self.analytics.get_historical_summary()

        except Exception as exc:
            raise DashboardServiceError(
                "Unable to retrieve experiment overview"
            ) from exc

        return {
            "total_experiments": len(reports),
            "completed_experiments": sum(
                1 for report in reports
                if report.get("experiment_status") == "completed"
            ),
            "failed_experiments": sum(
                1 for report in reports
                if report.get("experiment_status") == "failed"
            ),
            "average_success_rate": historical["average_success_rate"],
            "average_latency_ms": historical["average_latency_ms"],
            "total_retries": historical["total_retries"],
            "total_fallbacks": historical["total_fallbacks"],
        }

    def get_reliability_overview(self) -> dict:
        """Return reliability scores and risk distribution."""

        try:
            results = self.insights.analyze_all_experiments()

        except HistoricalInsightsError as exc:
            raise DashboardServiceError(
                "Unable to retrieve reliability insights"
            ) from exc

        total = len(results)

        risk_counts = {
            "low": sum(
                1 for item in results
                if item.risk_level == "low"
            ),
            "medium": sum(
                1 for item in results
                if item.risk_level == "medium"
            ),
            "high": sum(
                1 for item in results
                if item.risk_level == "high"
            ),
        }

        average_score = (
            sum(item.reliability_score for item in results) / total
            if total
            else 0.0
        )

        return {
            "average_reliability_score": round(average_score, 2),
            "low_risk_experiments": risk_counts["low"],
            "medium_risk_experiments": risk_counts["medium"],
            "high_risk_experiments": risk_counts["high"],
            "risk_distribution": risk_counts,
        }

    def get_recommendation_overview(self) -> dict:
        """Return recommendation management statistics."""

        try:
            return self.recommendation_manager.get_summary()

        except RecommendationManagerError as exc:
            raise DashboardServiceError(
                "Unable to retrieve recommendation overview"
            ) from exc

    def get_performance_trends(self) -> dict:
        """Return historical performance trends."""

        try:
            return {
                "success_rate": self.analytics.get_success_rate_trend(),
                "latency": self.analytics.get_latency_trend(),
                "retries": self.analytics.get_retry_trend(),
                "fallbacks": self.analytics.get_fallback_trend(),
            }

        except HistoricalAnalyticsError as exc:
            raise DashboardServiceError(
                "Unable to retrieve performance trends"
            ) from exc

    def get_experiment_highlights(self) -> dict:
        """Return the best and worst performing experiments."""

        try:
            best = self.analytics.get_best_experiment()
            worst = self.analytics.get_worst_experiment()

        except HistoricalAnalyticsError as exc:
            raise DashboardServiceError(
                "Unable to retrieve experiment highlights"
            ) from exc

        return {
            "best_experiment": best,
            "worst_experiment": worst,
        }

    def get_dashboard_data(self) -> dict:
        """Return all aggregated dashboard information."""

        try:
            return {
                "experiment_overview": self.get_experiment_overview(),
                "reliability_overview": self.get_reliability_overview(),
                "recommendation_overview": (
                    self.get_recommendation_overview()
                ),
                "performance_trends": self.get_performance_trends(),
                "experiment_highlights": (
                    self.get_experiment_highlights()
                ),
            }

        except DashboardServiceError:
            raise

        except Exception as exc:
            raise DashboardServiceError(
                "Unable to generate dashboard data"
            ) from exc
