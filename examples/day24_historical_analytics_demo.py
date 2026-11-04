
from agentfault.report_storage import ReportStorage
from agentfault.report_manager import ReportManager
from agentfault.historical_analytics import HistoricalAnalytics


def main():
    # 1. Initialize report management
    storage = ReportStorage("reports")
    manager = ReportManager(storage)

    # 2. Initialize historical analytics
    analytics = HistoricalAnalytics(manager)

    # 3. Display success-rate trends
    print("\nHISTORICAL SUCCESS RATE TRENDS")
    print("=" * 60)

    for item in analytics.get_success_rate_trend():
        print(
            f"{item['experiment_name']}: "
            f"{item['success_rate'] * 100:.2f}%"
        )

    # 4. Display latency trends
    print("\nHISTORICAL LATENCY TRENDS")
    print("=" * 60)

    for item in analytics.get_latency_trend():
        print(
            f"{item['experiment_name']}: "
            f"{item['average_latency_ms']:.4f} ms"
        )

    # 5. Display retry trends
    print("\nHISTORICAL RETRY TRENDS")
    print("=" * 60)

    for item in analytics.get_retry_trend():
        print(
            f"{item['experiment_name']}: "
            f"{item['total_retries']} retries"
        )

    # 6. Display fallback trends
    print("\nHISTORICAL FALLBACK TRENDS")
    print("=" * 60)

    for item in analytics.get_fallback_trend():
        print(
            f"{item['experiment_name']}: "
            f"{item['total_fallbacks']} fallbacks"
        )

    # 7. Identify best and worst experiments
    print("\nBEST AND WORST EXPERIMENTS")
    print("=" * 60)

    best = analytics.get_best_experiment()
    worst = analytics.get_worst_experiment()

    if best:
        print(
            f"Best: {best['experiment_name']} "
            f"({best['success_rate'] * 100:.2f}%)"
        )

    if worst:
        print(
            f"Worst: {worst['experiment_name']} "
            f"({worst['success_rate'] * 100:.2f}%)"
        )

    # 8. Compare two experiments
    reports = manager.list_reports()

    print("\nEXPERIMENT COMPARISON")
    print("=" * 60)

    if len(reports) >= 2:
        first_id = reports[0]["experiment_id"]
        second_id = reports[1]["experiment_id"]

        comparison = analytics.compare_experiments(
            first_id,
            second_id,
        )

        for key, value in comparison.items():
            print(f"{key}: {value}")

    # 9. Display overall historical summary
    print("\nHISTORICAL RELIABILITY SUMMARY")
    print("=" * 60)

    summary = analytics.get_historical_summary()

    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nHistorical analytics demonstration completed.")


if __name__ == "__main__":
    main()
