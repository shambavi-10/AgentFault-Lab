
from agentfault.agent_config import AgentConfig
from agentfault.agent_executor import execute_stochastic_sequence
from agentfault.benchmark import BenchmarkResult, calculate_benchmark
from agentfault.stochastic_scenarios import generate_stochastic_sequences


def run_stochastic_benchmark_suite(
    configs: list[AgentConfig],
    experiments: int = 100,
    timeout_probability: float = 0.1,
    rate_limit_probability: float = 0.1,
    seed: int | None = 42
) -> list[BenchmarkResult]:

    if not configs:
        raise ValueError("At least one agent configuration is required")

    if experiments < 1:
        raise ValueError("Experiments must be at least 1")

    # Generate enough outcomes for the agent with the most attempts.
    max_tool_calls = max(
        config.max_attempts for config in configs
    )

    # Generate sequences only once.
    # Every agent receives the same sequence for each experiment.
    sequences = generate_stochastic_sequences(
        experiments=experiments,
        tool_calls_per_experiment=max_tool_calls,
        timeout_probability=timeout_probability,
        rate_limit_probability=rate_limit_probability,
        seed=seed
    )

    benchmark_results = []

    for config in configs:

        successful_executions = 0
        total_retries = 0
        total_latency = 0.0
        total_backoff_seconds = 0.0
        evaluation_scores = []
        run_success_rates = []

        for sequence in sequences:

            execution = execute_stochastic_sequence(
                config=config,
                outcomes=sequence.copy()
            )

            is_successful = execution.valid_business_result

            if is_successful:
                successful_executions += 1

            total_retries += execution.retry_count

            total_latency += (
                execution.execution_time_ms / 1000
            )

            total_backoff_seconds += (
                execution.scheduled_backoff_seconds
            )

            evaluation_scores.append(float(is_successful))

            run_success_rates.append(float(is_successful))

        result = calculate_benchmark(
            agent_name=config.name,
            total_executions=experiments,
            successful_executions=successful_executions,
            total_retries=total_retries,
            total_latency=total_latency,
            evaluation_scores=evaluation_scores,
            total_backoff_seconds=total_backoff_seconds,
            run_success_rates=run_success_rates
        )

        benchmark_results.append(result)

    return benchmark_results
