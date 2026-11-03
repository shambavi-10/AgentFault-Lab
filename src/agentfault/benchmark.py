
from dataclasses import dataclass
from statistics import mean, pstdev


@dataclass
class BenchmarkResult:
    """Stores the performance results of one agent configuration."""

    agent_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    average_latency: float
    total_retries: int
    average_evaluation_score: float
    total_backoff_seconds: float
    mean_run_success_rate: float = 0.0
    success_rate_std_dev: float = 0.0


def calculate_benchmark(
    agent_name: str,
    total_executions: int,
    successful_executions: int,
    total_retries: int,
    total_latency: float,
    evaluation_scores: list[float],
    total_backoff_seconds: float = 0.0,
    run_success_rates: list[float] | None = None
) -> BenchmarkResult:
    """Calculate benchmark metrics for one agent configuration."""

    if total_executions <= 0:
        raise ValueError("Total executions must be greater than zero")

    if not 0 <= successful_executions <= total_executions:
        raise ValueError(
            "Successful executions must be between zero and total executions"
        )

    if total_retries < 0:
        raise ValueError("Total retries cannot be negative")

    if total_latency < 0:
        raise ValueError("Total latency cannot be negative")

    if total_backoff_seconds < 0:
        raise ValueError("Total backoff cannot be negative")

    if not evaluation_scores:
        raise ValueError("At least one evaluation score is required")

    if any(
        not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not 0 <= score <= 1
        for score in evaluation_scores
    ):
        raise ValueError("Evaluation scores must be between 0 and 1")

    if run_success_rates is None:
        run_success_rates = [successful_executions / total_executions]

    if not run_success_rates:
        raise ValueError("At least one run success rate is required")

    if any(
        not isinstance(rate, (int, float))
        or isinstance(rate, bool)
        or not 0 <= rate <= 1
        for rate in run_success_rates
    ):
        raise ValueError("Run success rates must be between 0 and 1")

    failed_executions = total_executions - successful_executions
    success_rate = successful_executions / total_executions
    average_latency = total_latency / total_executions
    average_evaluation_score = mean(evaluation_scores)

    mean_run_success_rate = mean(run_success_rates)
    success_rate_std_dev = pstdev(run_success_rates)

    return BenchmarkResult(
        agent_name=agent_name,
        total_executions=total_executions,
        successful_executions=successful_executions,
        failed_executions=failed_executions,
        success_rate=round(success_rate, 2),
        average_latency=round(average_latency, 4),
        total_retries=total_retries,
        average_evaluation_score=round(average_evaluation_score, 2),
        total_backoff_seconds=round(total_backoff_seconds, 4),
        mean_run_success_rate=round(mean_run_success_rate, 4),
        success_rate_std_dev=round(success_rate_std_dev, 4)
    )


def compare_agents(
    results: list[BenchmarkResult]
) -> list[BenchmarkResult]:
    """Rank agents by evaluation score, success rate, and retry count."""

    return sorted(
        results,
        key=lambda result: (
            -result.average_evaluation_score,
            -result.success_rate,
            result.total_retries
        )
    )


def generate_benchmark_report(
    results: list[BenchmarkResult]
) -> str:
    """Generate a readable report comparing agent configurations."""

    ranked_results = compare_agents(results)

    if not ranked_results:
        return "No benchmark results available."

    lines = [
        "AGENTFAULT LAB - BENCHMARK REPORT",
        "=" * 60,
        ""
    ]

    for rank, result in enumerate(ranked_results, start=1):
        lines.extend([
            f"Rank: {rank}",
            f"Agent: {result.agent_name}",
            f"Executions: {result.total_executions}",
            f"Valid business successes: {result.successful_executions}",
            f"Failed executions: {result.failed_executions}",
            f"Valid success rate: {result.success_rate * 100:.2f}%",
            f"Mean run success rate: {result.mean_run_success_rate * 100:.2f}%",
            f"Success rate standard deviation: {result.success_rate_std_dev * 100:.2f} percentage points",
            f"Average processing latency: {result.average_latency:.4f} seconds",
            f"Total retries: {result.total_retries}",
            f"Total scheduled backoff: {result.total_backoff_seconds:.4f} seconds",
            f"Average evaluation score: "
            f"{result.average_evaluation_score:.2f}",
            "-" * 60
        ])

    lines.append("End of benchmark report")

    return "\n".join(lines)
