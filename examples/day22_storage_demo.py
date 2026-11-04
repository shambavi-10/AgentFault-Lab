
from agentfault.experiment import Experiment
from agentfault.scenarios import FailureScenario
from agentfault.reliability_config import ReliabilityConfig
from agentfault.experiment_executor import execute_experiment
from agentfault.benchmark_analytics import calculate_benchmark_analytics
from agentfault.benchmark_report import (
    generate_benchmark_report,
    format_benchmark_report,
)
from agentfault.report_storage import ReportStorage


def main():
    # 1. Create scenarios
    scenarios = [
        FailureScenario(
            name="Normal Execution",
            failure_sequence=["none"],
        ),
        FailureScenario(
            name="Timeout Recovery",
            failure_sequence=["timeout", "none"],
        ),
        FailureScenario(
            name="Rate Limit Recovery",
            failure_sequence=["rate_limit", "none"],
        ),
    ]

    # 2. Configure reliability
    config = ReliabilityConfig(
        max_attempts=3,
        retry_strategy="fixed",
        base_delay=0,
        jitter=False,
        enable_circuit_breaker=False,
        enable_fallback=False,
    )

    # 3. Create experiment
    experiment = Experiment(
        name="Day 22 Storage Demo",
        description="Demonstrates persistent benchmark report storage.",
        scenarios=scenarios,
        reliability_config=config,
    )

    # 4. Execute experiment
    execution = execute_experiment(experiment)

    # 5. Calculate analytics
    analytics = calculate_benchmark_analytics(execution)

    # 6. Generate report
    report = generate_benchmark_report(execution, analytics)

    # 7. Initialize storage
    storage = ReportStorage("reports")

    # 8. Save report
    saved_path = storage.save_report(report)
    print(f"\nReport saved successfully: {saved_path}")

    # 9. Retrieve report
    retrieved_report = storage.get_report(report.experiment_id)

    print("\nRetrieved Report:")
    print(f"Experiment: {retrieved_report['experiment_name']}")
    print(f"Success Rate: {retrieved_report['success_rate'] * 100:.2f}%")
    print(f"Total Retries: {retrieved_report['total_retries']}")

    # 10. List all reports
    reports = storage.list_reports()
    print(f"\nTotal stored reports: {len(reports)}")

    # 11. Display complete report
    print("\n")
    print(format_benchmark_report(report))


if __name__ == "__main__":
    main()
