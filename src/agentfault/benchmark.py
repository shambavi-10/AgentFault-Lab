from dataclasses import dataclass


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


def calculate_benchmark(
    agent_name: str,
    total_executions: int,
    successful_executions: int,
    total_retries: int,
    total_latency: float,
    evaluation_scores: list[float]
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

    if not evaluation_scores:
        raise ValueError("At least one evaluation score is required")

    if any(score < 0 or score > 1 for score in evaluation_scores):
        raise ValueError("Evaluation scores must be between 0 and 1")

    failed_executions = total_executions - successful_executions
    success_rate = successful_executions / total_executions
    average_latency = total_latency / total_executions

    average_evaluation_score = (
        sum(evaluation_scores) / len(evaluation_scores)
    )

    return BenchmarkResult(
        agent_name=agent_name,
        total_executions=total_executions,
        successful_executions=successful_executions,
        failed_executions=failed_executions,
        success_rate=round(success_rate, 2),
        average_latency=round(average_latency, 4),
        total_retries=total_retries,
        average_evaluation_score=round(average_evaluation_score, 2)
    )

def compare_agents(
    results: list[BenchmarkResult]
) -> list[BenchmarkResult]:
    """Rank agents by success rate, evaluation score, and latency."""

    return sorted(
        results,
        key=lambda result: (
            -result.success_rate,
            -result.average_evaluation_score,
            result.average_latency
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
            f"Successful: {result.successful_executions}",
            f"Failed: {result.failed_executions}",
            f"Success rate: {result.success_rate * 100:.2f}%",
            f"Average latency: {result.average_latency:.4f} seconds",
            f"Total retries: {result.total_retries}",
            f"Average evaluation score: "
            f"{result.average_evaluation_score:.2f}",
            "-" * 60
        ])

    lines.append("End of benchmark report")

    return "\n".join(lines)