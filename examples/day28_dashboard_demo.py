
from agentfault.historical_analytics import HistoricalAnalytics
from agentfault.historical_insights import HistoricalInsights
from agentfault.recommendation_manager import RecommendationManager
from agentfault.report_manager import ReportManager
from agentfault.report_storage import ReportStorage
from agentfault.dashboard_service import DashboardService


def main():
    # Initialize report infrastructure
    storage = ReportStorage("reports")
    report_manager = ReportManager(storage)

    # Initialize analytics and insights
    analytics = HistoricalAnalytics(report_manager)
    insights = HistoricalInsights(analytics)

    # Initialize recommendation management
    recommendation_manager = RecommendationManager(
        "recommendations.json"
    )

    # Initialize dashboard service
    dashboard = DashboardService(
        analytics,
        insights,
        recommendation_manager,
    )

    # Generate complete dashboard data
    data = dashboard.get_dashboard_data()

    # Experiment overview
    print("\n========== EXPERIMENT OVERVIEW ==========")

    for key, value in data["experiment_overview"].items():
        print(f"{key}: {value}")

    # Reliability overview
    print("\n========== RELIABILITY OVERVIEW ==========")

    for key, value in data["reliability_overview"].items():
        print(f"{key}: {value}")

    # Recommendation overview
    print("\n========== RECOMMENDATION OVERVIEW ==========")

    for key, value in data["recommendation_overview"].items():
        print(f"{key}: {value}")

    # Performance trends
    print("\n========== PERFORMANCE TRENDS ==========")

    for category, records in data["performance_trends"].items():
        print(f"\n{category.upper()}")

        for record in records:
            print(record)

    # Best and worst experiments
    print("\n========== EXPERIMENT HIGHLIGHTS ==========")

    highlights = data["experiment_highlights"]

    print("Best experiment:", highlights["best_experiment"])
    print("Worst experiment:", highlights["worst_experiment"])

    print("\nDashboard data generated successfully.")


if __name__ == "__main__":
    main()
