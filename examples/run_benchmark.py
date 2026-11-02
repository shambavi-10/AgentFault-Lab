from agentfault.benchmark import (
    calculate_benchmark,
    generate_benchmark_report
)


def main():
    # Agent A: No retries
    agent_a = calculate_benchmark(
        agent_name="Agent A - No Retry",
        total_executions=10,
        successful_executions=6,
        total_retries=0,
        total_latency=8.0,
        evaluation_scores=[0.9, 0.8, 0.7, 0.9, 0.8]
    )

    # Agent B: Basic retries
    agent_b = calculate_benchmark(
        agent_name="Agent B - Basic Retry",
        total_executions=10,
        successful_executions=8,
        total_retries=5,
        total_latency=15.0,
        evaluation_scores=[0.9, 0.9, 0.8, 0.9, 0.9]
    )

    # Agent C: Retry with exponential backoff
    agent_c = calculate_benchmark(
        agent_name="Agent C - Exponential Backoff",
        total_executions=10,
        successful_executions=9,
        total_retries=7,
        total_latency=18.0,
        evaluation_scores=[1.0, 0.9, 0.9, 1.0, 0.9]
    )

    results = [agent_a, agent_b, agent_c]

    report = generate_benchmark_report(results)

    print(report)


if __name__ == "__main__":
    main()