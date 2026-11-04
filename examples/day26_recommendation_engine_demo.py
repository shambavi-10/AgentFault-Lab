
from agentfault.report_storage import ReportStorage
from agentfault.report_manager import ReportManager
from agentfault.historical_analytics import HistoricalAnalytics
from agentfault.historical_insights import HistoricalInsights
from agentfault.recommendation_engine import RecommendationEngine


def main():
    storage = ReportStorage("reports")
    manager = ReportManager(storage)

    analytics = HistoricalAnalytics(manager)
    insights = HistoricalInsights(analytics)

    engine = RecommendationEngine(insights)

    recommendations = engine.generate_all_recommendations()

    print("\nAGENTFAULT LAB")
    print("RELIABILITY RECOMMENDATION ENGINE")
    print("=" * 70)

    if not recommendations:
        print("\nNo saved experiment reports found.")

    else:
        for recommendation in recommendations:
            print(f"\nExperiment: {recommendation.experiment_name}")
            print(f"Category: {recommendation.category.upper()}")
            print(f"Priority: {recommendation.priority.upper()}")
            print(f"Title: {recommendation.title}")

            print(f"\nProblem:")
            print(recommendation.description)

            print("\nRecommended Action:")
            print(recommendation.action)

            print("-" * 70)

    # Priority summary
    print("\nRECOMMENDATION SUMMARY")
    print("=" * 70)

    for priority in ["critical", "high", "medium", "low"]:
        count = sum(
            item.priority == priority
            for item in recommendations
        )

        print(f"{priority.upper()}: {count}")

    print(f"\nTotal recommendations: {len(recommendations)}")

    print("\nRecommendation analysis completed.")


if __name__ == "__main__":
    main()
