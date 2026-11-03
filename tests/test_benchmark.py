import pytest

from agentfault.benchmark import calculate_benchmark, BenchmarkResult


def test_calculate_benchmark_success():
    result = calculate_benchmark(
        agent_name="Agent A",
        total_executions=10,
        successful_executions=8,
        total_retries=5,
        total_latency=20.0,
        evaluation_scores=[1.0, 0.8, 0.9, 0.7]
    )

    assert isinstance(result, BenchmarkResult)
    assert result.agent_name == "Agent A"
    assert result.total_executions == 10
    assert result.successful_executions == 8
    assert result.failed_executions == 2
    assert result.success_rate == 0.8
    assert result.average_latency == 2.0
    assert result.total_retries == 5
    assert result.average_evaluation_score == 0.85


def test_zero_executions_raises_error():
    with pytest.raises(ValueError):
        calculate_benchmark(
            "Agent A", 0, 0, 0, 0.0, [0.8]
        )


def test_successful_executions_cannot_exceed_total():
    with pytest.raises(ValueError):
        calculate_benchmark(
            "Agent A", 10, 11, 0, 10.0, [0.8]
        )


def test_negative_retries_raise_error():
    with pytest.raises(ValueError):
        calculate_benchmark(
            "Agent A", 10, 8, -1, 10.0, [0.8]
        )


def test_negative_latency_raises_error():
    with pytest.raises(ValueError):
        calculate_benchmark(
            "Agent A", 10, 8, 0, -1.0, [0.8]
        )


def test_empty_evaluation_scores_raise_error():
    with pytest.raises(ValueError):
        calculate_benchmark(
            "Agent A", 10, 8, 0, 10.0, []
        )


def test_evaluation_score_above_one_raises_error():
    with pytest.raises(ValueError):
        calculate_benchmark(
            "Agent A", 10, 8, 0, 10.0, [1.2]
        )


def test_negative_evaluation_score_raises_error():
    with pytest.raises(ValueError):
        calculate_benchmark(
            "Agent A", 10, 8, 0, 10.0, [-0.1]
        )

def test_compare_agents_ranks_by_success_rate():
    from agentfault.benchmark import compare_agents

    agent_a = calculate_benchmark(
        "Agent A", 10, 7, 0, 12.0, [0.9]
    )

    agent_b = calculate_benchmark(
        "Agent B", 10, 9, 2, 20.0, [0.8]
    )

    agent_c = calculate_benchmark(
        "Agent C", 10, 9, 3, 15.0, [0.95]
    )

    ranked = compare_agents([agent_a, agent_b, agent_c])

    assert [agent.agent_name for agent in ranked] == [
        "Agent C",
        "Agent A",
        "Agent B"
    ]


def test_compare_agents_uses_evaluation_score_as_tiebreaker():
    from agentfault.benchmark import compare_agents

    agent_a = calculate_benchmark(
        "Agent A", 10, 9, 1, 10.0, [0.8]
    )

    agent_b = calculate_benchmark(
        "Agent B", 10, 9, 1, 10.0, [0.95]
    )

    ranked = compare_agents([agent_a, agent_b])

    assert ranked[0].agent_name == "Agent B"


def test_compare_agents_does_not_rank_by_latency():
    from agentfault.benchmark import compare_agents

    agent_a = calculate_benchmark(
        "Agent A", 10, 9, 1, 20.0, [0.9]
    )

    agent_b = calculate_benchmark(
        "Agent B", 10, 9, 1, 10.0, [0.9]
    )

    ranked = compare_agents([agent_a, agent_b])

    # Equal ranking metrics: preserve original order.
    assert ranked[0].agent_name == "Agent A"
    assert ranked[1].agent_name == "Agent B"


def test_compare_agents_handles_empty_list():
    from agentfault.benchmark import compare_agents

    assert compare_agents([]) == []

def test_generate_benchmark_report():
    from agentfault.benchmark import generate_benchmark_report

    agent_a = calculate_benchmark(
        "Agent A", 10, 7, 0, 12.0, [0.9]
    )

    agent_b = calculate_benchmark(
        "Agent B", 10, 9, 2, 20.0, [0.8]
    )

    report = generate_benchmark_report([agent_a, agent_b])

    assert "AGENTFAULT LAB - BENCHMARK REPORT" in report
    assert "Agent B" in report
    assert "Agent A" in report
    assert "Valid success rate: 90.00%" in report
    assert "Rank: 1" in report
    assert "End of benchmark report" in report


def test_generate_benchmark_report_with_empty_results():
    from agentfault.benchmark import generate_benchmark_report

    report = generate_benchmark_report([])

    assert report == "No benchmark results available."

def test_benchmark_calculates_mean_run_success_rate():

    result = calculate_benchmark(
        agent_name="Mean Test Agent",
        total_executions=4,
        successful_executions=3,
        total_retries=2,
        total_latency=4.0,
        evaluation_scores=[1.0, 1.0, 0.0, 1.0],
        run_success_rates=[0.5, 1.0, 0.5, 1.0]
    )

    assert result.mean_run_success_rate == 0.75


def test_benchmark_calculates_success_rate_standard_deviation():

    result = calculate_benchmark(
        agent_name="Stability Test Agent",
        total_executions=4,
        successful_executions=3,
        total_retries=2,
        total_latency=4.0,
        evaluation_scores=[1.0, 1.0, 0.0, 1.0],
        run_success_rates=[0.5, 1.0, 0.5, 1.0]
    )

    assert result.success_rate_std_dev == 0.25


def test_identical_run_success_rates_have_zero_standard_deviation():

    result = calculate_benchmark(
        agent_name="Consistent Agent",
        total_executions=4,
        successful_executions=4,
        total_retries=0,
        total_latency=2.0,
        evaluation_scores=[1.0, 1.0, 1.0, 1.0],
        run_success_rates=[1.0, 1.0, 1.0, 1.0]
    )

    assert result.mean_run_success_rate == 1.0
    assert result.success_rate_std_dev == 0.0

