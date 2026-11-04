from agentfault.experiment import Experiment
from agentfault.scenarios import FailureScenario
from agentfault.reliability_config import ReliabilityConfig
from agentfault.experiment_executor import execute_experiment
from agentfault.benchmark_analytics import calculate_benchmark_analytics
from agentfault.benchmark_report import (
    generate_benchmark_report,
    format_benchmark_report,
    export_benchmark_report_json,
)
import json

def main():
    # 1. Define test scenarios
    scenarios = [
        FailureScenario(
            name="Normal Execution",
            failure_sequence=["none"],
            expected_status="success",
        ),
        FailureScenario(
            name="Timeout Recovery",
            failure_sequence=["timeout", "none"],
            expected_status="success",
        ),
        FailureScenario(
            name="Rate Limit Recovery",
            failure_sequence=["rate_limit", "none"],
            expected_status="success",
        ),
    ]

    # 2. Configure reliability strategy
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
        name="Day 21 Benchmark Report Demo",
        description="Demonstrates benchmark report generation.",
        scenarios=scenarios,
        reliability_config=config,
    )

    # 4. Execute experiment
    execution = execute_experiment(experiment)

    # 5. Calculate analytics
    analytics = calculate_benchmark_analytics(execution)

    # 6. Generate benchmark report
    report = generate_benchmark_report(
        execution=execution,
        analytics=analytics,
    )
    # 7. Export report as JSON
    report_data = export_benchmark_report_json(report)

    json_output = json.dumps(
        report_data,
        indent=4,
    )

    print("\nJSON BENCHMARK REPORT")
    print("=" * 60)
    print(json_output)

    # 7. Display human-readable report
    print(format_benchmark_report(report))


if __name__ == "__main__":
    main()
