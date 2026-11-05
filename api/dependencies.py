from functools import lru_cache

from agentfault.report_storage import ReportStorage
from agentfault.report_manager import ReportManager
from agentfault.historical_analytics import HistoricalAnalytics
from agentfault.historical_insights import HistoricalInsights
from agentfault.recommendation_manager import RecommendationManager
from agentfault.dashboard_service import DashboardService
from agentfault.recommendation_engine import RecommendationEngine


@lru_cache
def get_report_manager() -> ReportManager:
    """Create and reuse the report manager."""

    report_storage = ReportStorage(storage_dir="reports")
    return ReportManager(report_storage)


@lru_cache
def get_historical_analytics() -> HistoricalAnalytics:
    """Create and reuse the historical analytics service."""

    return HistoricalAnalytics(get_report_manager())


@lru_cache
def get_historical_insights() -> HistoricalInsights:
    """Create and reuse the historical insights service."""

    return HistoricalInsights(get_historical_analytics())


@lru_cache
def get_recommendation_engine() -> RecommendationEngine:
    """Create and reuse the reliability recommendation engine."""

    return RecommendationEngine(
        insights=get_historical_insights()
    )


@lru_cache
def get_recommendation_manager() -> RecommendationManager:
    """Create and reuse the recommendation manager."""

    return RecommendationManager(
        storage_path="recommendations.json"
    )


@lru_cache
def get_dashboard_service() -> DashboardService:
    """Create and reuse the dashboard service and its dependencies."""

    return DashboardService(
        analytics=get_historical_analytics(),
        insights=get_historical_insights(),
        recommendation_manager=get_recommendation_manager(),
    )