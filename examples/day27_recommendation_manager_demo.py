
from agentfault.historical_analytics import HistoricalAnalytics
from agentfault.historical_insights import HistoricalInsights
from agentfault.recommendation_engine import RecommendationEngine
from agentfault.recommendation_manager import RecommendationManager
from agentfault.report_manager import ReportManager
from agentfault.report_storage import ReportStorage


def main():
    # Initialize existing report infrastructure
    storage = ReportStorage("reports")
    report_manager = ReportManager(storage)

    analytics = HistoricalAnalytics(report_manager)
    insights = HistoricalInsights(analytics)

    # Initialize Day 26 recommendation engine
    engine = RecommendationEngine(insights)

    # Initialize Day 27 recommendation manager
    manager = RecommendationManager(
        "recommendations.json"
    )

    # Generate recommendations
    print("\nGenerating reliability recommendations...")

    generated = engine.generate_all_recommendations()

    print(f"Generated recommendations: {len(generated)}")

    # Save recommendations
    saved = manager.add_recommendations(generated)

    print(f"New recommendations saved: {len(saved)}")

    # Display all recommendations
    recommendations = manager.list_recommendations()

    print("\n========== RECOMMENDATIONS ==========")

    for item in recommendations:
        print(f"\nID: {item['recommendation_id']}")
        print(f"Experiment: {item['experiment_name']}")
        print(f"Category: {item['category']}")
        print(f"Priority: {item['priority'].upper()}")
        print(f"Title: {item['title']}")
        print(f"Status: {item['status']}")

    # Demonstrate assignment and progress tracking
    if recommendations:
        first = recommendations[0]
        recommendation_id = first["recommendation_id"]

        print("\n========== MANAGEMENT DEMO ==========")

        manager.assign_recommendation(
            recommendation_id,
            "Reliability Engineering Team",
        )

        manager.update_status(
            recommendation_id,
            "in_progress",
        )

        manager.add_note(
            recommendation_id,
            "Investigation started. Reviewing execution traces.",
        )

        print("Recommendation assigned successfully.")
        print("Status updated to in_progress.")
        print("Progress note added.")

    # Display management summary
    summary = manager.get_summary()

    print("\n========== MANAGEMENT SUMMARY ==========")

    print(f"Total recommendations: {summary['total_recommendations']}")
    print(f"Open: {summary['open']}")
    print(f"In progress: {summary['in_progress']}")
    print(f"Resolved: {summary['resolved']}")
    print(f"Resolution rate: {summary['resolution_rate']:.2f}%")

    print("\nPriority distribution:")

    for priority, count in summary["priority_counts"].items():
        print(f"{priority.upper()}: {count}")


if __name__ == "__main__":
    main()
