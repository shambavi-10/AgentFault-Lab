
from functools import lru_cache

from agentfault.report_storage import ReportStorage
from agentfault.report_manager import ReportManager
from agentfault.historical_analytics import HistoricalAnalytics
from agentfault.historical_insights import HistoricalInsights
from agentfault.recommendation_manager import RecommendationManager
from agentfault.dashboard_service import DashboardService
from agentfault.recommendation_engine import RecommendationEngine

@lru_cache
def get_dashboard_service() -> DashboardService:
    """Create and reuse the dashboard service and its dependencies."""

    report_storage = ReportStorage(storage_dir="reports")

    report_manager = ReportManager(
        report_storage
    )

    analytics = HistoricalAnalytics(
        report_manager
    )

    insights = HistoricalInsights(
        analytics
    )

    recommendation_manager = RecommendationManager(
        storage_path="recommendations.json"
    )

    return DashboardService(
        analytics=analytics,
        insights=insights,
        recommendation_manager=recommendation_manager,
    )
@lru_cache
def get_report_manager() -> ReportManager:
    """Create and reuse the report manager."""

    report_storage = ReportStorage(
        storage_dir="reports"
    )

    return ReportManager(report_storage)

@lru_cache
def get_recommendation_engine() -> RecommendationEngine:
    """Create and reuse the reliability recommendation engine."""

    report_manager = get_report_manager()

    analytics = HistoricalAnalytics(
        report_manager
    )

    insights = HistoricalInsights(
        analytics
    )

    return RecommendationEngine(
        insights=insights
    )


@lru_cache
def get_recommendation_manager() -> RecommendationManager:
    """Create and reuse the recommendation manager."""

    return RecommendationManager(
        storage_path="recommendations.json"
    )