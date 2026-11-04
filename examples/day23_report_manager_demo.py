
from agentfault.report_storage import ReportStorage
from agentfault.report_manager import ReportManager
from agentfault.benchmark_report import (
    BenchmarkReport,
    ScenarioReport,
)


def create_sample_report(
    experiment_id,
    experiment_name,
    status,
    success_rate,
):
    return BenchmarkReport(
        experiment_id=experiment_id,
        experiment_name=experiment_name,
        experiment_status=status,
        total_scenarios=5,
        passed_scenarios=round(5 * success_rate),
        failed_scenarios=5 - round(5 * success_rate),
        success_rate=success_rate,
        failure_rate=1 - success_rate,
        average_latency_ms=25.0,
        minimum_latency_ms=10.0,
        maximum_latency_ms=50.0,
        p50_latency_ms=20.0,
        p90_latency_ms=45.0,
        p95_latency_ms=48.0,
        p99_latency_ms=50.0,
        total_retries=3,
        average_retries=0.6,
        total_fallbacks=1,
        fallback_usage_rate=0.2,
        scenario_reports=[
            ScenarioReport(
                scenario_name=f"Scenario {index}",
                expected_status="success",
                actual_status="success" if index <= round(5 * success_rate) else "failure",
                passed=index <= round(5 * success_rate),
                execution_time_ms=20.0 + index,
                retry_count=0,
                fallback_count=0,
            )
            for index in range(1, 6)
        ],
    )


def main():
    # 1. Initialize storage and manager
    storage = ReportStorage("reports")
    manager = ReportManager(storage)

    # 2. Create sample reports
    reports = [
        create_sample_report(
            "demo-001",
            "Normal Agent Execution",
            "completed",
            1.0,
        ),
        create_sample_report(
            "demo-002",
            "Unstable Agent Execution",
            "failed",
            0.4,
        ),
        create_sample_report(
            "demo-003",
            "Retry Recovery Experiment",
            "completed",
            0.8,
        ),
    ]

    # 3. Save reports
    print("\nSAVING REPORTS")
    print("-" * 45)

    for report in reports:
        path = storage.save_report(report)
        print(f"Saved: {report.experiment_name} -> {path}")

    # 4. Retrieve a specific report
    print("\nRETRIEVING REPORT")
    print("-" * 45)

    retrieved = manager.get_report("demo-001")

    if retrieved:
        print(f"Experiment: {retrieved['experiment_name']}")
        print(f"Success Rate: {retrieved['success_rate'] * 100:.2f}%")

    # 5. List all reports
    print("\nALL STORED REPORTS")
    print("-" * 45)

    for report in manager.list_reports():
        print(
            f"{report['experiment_id']} | "
            f"{report['experiment_name']} | "
            f"{report['experiment_status']}"
        )

    # 6. Filter completed reports
    print("\nCOMPLETED REPORTS")
    print("-" * 45)

    completed = manager.filter_reports("completed")

    for report in completed:
        print(report["experiment_name"])

    # 7. Display summary
    print("\nREPORT SUMMARY")
    print("-" * 45)

    summary = manager.get_summary()

    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
