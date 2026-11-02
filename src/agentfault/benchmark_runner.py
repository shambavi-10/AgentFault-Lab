
from agentfault.agent_config import AgentConfig
from agentfault.agent_executor import execute_scenario
from agentfault.benchmark import BenchmarkResult, calculate_benchmark
from agentfault.scenarios import FailureScenario


def run_benchmark_suite(
    configs: list[AgentConfig],
    scenarios: list[FailureScenario]
) -> list[BenchmarkResult]:

    if not configs:
        raise ValueError("At least one agent configuration is required")

    if not scenarios:
        raise ValueError("At least one scenario is required")

    benchmark_results = []

    for config in configs:
        successful_executions = 0
        total_retries = 0
        total_latency = 0.0
        total_backoff_seconds = 0.0
        evaluation_scores = []

        for scenario in scenarios:
            execution = execute_scenario(config, scenario)

            # Count only valid business results as successes.
            if execution.valid_business_result:
                successful_executions += 1

            total_retries += execution.retry_count
            total_latency += execution.execution_time_ms / 1000

            total_backoff_seconds += (
                execution.scheduled_backoff_seconds
            )

            # Evaluate expected scenario outcome.
            score = float(
                execution.result.status == scenario.expected_status
                and (
                    scenario.expected_status == "failure"
                    or execution.valid_business_result
                )
            )

            evaluation_scores.append(score)

        result = calculate_benchmark(
            agent_name=config.name,
            total_executions=len(scenarios),
            successful_executions=successful_executions,
            total_retries=total_retries,
            total_latency=total_latency,
            evaluation_scores=evaluation_scores,
            total_backoff_seconds=total_backoff_seconds
        )

        benchmark_results.append(result)

    return benchmark_results
