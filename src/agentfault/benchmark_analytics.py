
from dataclasses import dataclass
from math import ceil, isfinite

from agentfault.experiment_executor import ExperimentExecution


@dataclass
class BenchmarkAnalytics:
    """Stores analytics calculated from an experiment execution."""

    experiment_id: str
    experiment_name: str

    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int

    success_rate: float
    failure_rate: float

    average_latency_ms: float
    minimum_latency_ms: float
    maximum_latency_ms: float

    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float

    total_retries: int
    average_retries: float

    total_fallbacks: int
    fallback_usage_rate: float


def calculate_percentile(
    values: list[float],
    percentile: float,
) -> float:
    """Calculate percentile using the nearest-rank method."""

    if not values:
        raise ValueError("Cannot calculate percentile of empty data")

    if not 0 < percentile <= 100:
        raise ValueError("Percentile must be greater than 0 and at most 100")

    if any(not isfinite(value) or value < 0 for value in values):
        raise ValueError("Values must be finite and non-negative")

    sorted_values = sorted(values)

    rank = ceil((percentile / 100) * len(sorted_values))

    return sorted_values[rank - 1]


def calculate_benchmark_analytics(
    execution: ExperimentExecution,
) -> BenchmarkAnalytics:
    """Calculate benchmark analytics from experiment execution results."""

    if execution.total_scenarios <= 0:
        raise ValueError("Experiment must contain at least one scenario")

    scenario_results = execution.scenario_results

    if len(scenario_results) != execution.total_scenarios:
        raise ValueError("Scenario count does not match execution results")

    latencies = [
        result.execution_time_ms
        for result in scenario_results
    ]

    if any(not isfinite(value) or value < 0 for value in latencies):
        raise ValueError("Execution times must be finite and non-negative")

    total_scenarios = execution.total_scenarios
    passed_scenarios = sum(result.passed for result in scenario_results)
    failed_scenarios = total_scenarios - passed_scenarios

    success_rate = passed_scenarios / total_scenarios
    failure_rate = failed_scenarios / total_scenarios

    total_execution_time = sum(latencies)

    average_latency = total_execution_time / total_scenarios

    total_retries = sum(
        result.retry_count
        for result in scenario_results
    )

    total_fallbacks = sum(
        result.fallback_count
        for result in scenario_results
    )

    average_retries = total_retries / total_scenarios

    fallback_usage_rate = (
        sum(result.fallback_used for result in scenario_results)
        / total_scenarios
    )

    return BenchmarkAnalytics(
        experiment_id=execution.experiment_id,
        experiment_name=execution.experiment_name,
        total_scenarios=total_scenarios,
        passed_scenarios=passed_scenarios,
        failed_scenarios=failed_scenarios,
        success_rate=round(success_rate, 4),
        failure_rate=round(failure_rate, 4),
        average_latency_ms=round(average_latency, 4),
        minimum_latency_ms=round(min(latencies), 4),
        maximum_latency_ms=round(max(latencies), 4),
        p50_latency_ms=round(calculate_percentile(latencies, 50), 4),
        p90_latency_ms=round(calculate_percentile(latencies, 90), 4),
        p95_latency_ms=round(calculate_percentile(latencies, 95), 4),
        p99_latency_ms=round(calculate_percentile(latencies, 99), 4),
        total_retries=total_retries,
        average_retries=round(average_retries, 4),
        total_fallbacks=total_fallbacks,
        fallback_usage_rate=round(fallback_usage_rate, 4),
    )
