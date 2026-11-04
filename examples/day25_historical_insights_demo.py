
from agentfault.report_storage import ReportStorage
from agentfault.report_manager import ReportManager
from agentfault.historical_analytics import HistoricalAnalytics
from agentfault.historical_insights import HistoricalInsights


def main():
    storage = ReportStorage("reports")
    manager = ReportManager(storage)
    analytics = HistoricalAnalytics(manager)

    insights_engine = HistoricalInsights(
        analytics,
        target_latency_ms=1000,
        max_average_retries=1,
        max_fallback_usage_rate=0.2,
    )

    results = insights_engine.analyze_all_experiments()

    print("\nAGENTFAULT LAB — HISTORICAL RELIABILITY INSIGHTS")
    print("=" * 65)

    for result in results:
        print(f"\nExperiment: {result.experiment_name}")
        print("-" * 65)

        print(f"Reliability Score: {result.reliability_score}/100")
        print(f"Risk Level: {result.risk_level.upper()}")

        print("\nScore Breakdown:")
        print(f"  Success:  {result.success_score}/50")
        print(f"  Latency:  {result.latency_score}/20")
        print(f"  Retries:  {result.retry_score}/15")
        print(f"  Fallback: {result.fallback_score}/15")

        print("\nDetected Issues:")

        if result.issues:
            for issue in result.issues:
                print(f"  - {issue}")
        else:
            print("  No major issues detected.")

        print("\nRecommendations:")

        for recommendation in result.recommendations:
            print(f"  - {recommendation}")

    print("\n" + "=" * 65)
    print("Historical insights analysis completed.")


if __name__ == "__main__":
    main()
