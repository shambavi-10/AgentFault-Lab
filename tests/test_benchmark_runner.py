
from agentfault.agent_config import AgentConfig
from agentfault.benchmark_runner import run_benchmark_suite
from agentfault.scenarios import FailureScenario


def test_malformed_output_is_not_counted_as_valid_success():

    config = AgentConfig(
        name="Malformed Agent",
        max_attempts=1,
        retry_strategy="none"
    )

    scenario = FailureScenario(
        name="Malformed Output",
        failure_sequence=["malformed"],
        expected_status="success"
    )

    results = run_benchmark_suite(
        configs=[config],
        scenarios=[scenario]
    )

    result = results[0]

    assert result.successful_executions == 0
    assert result.failed_executions == 1
    assert result.success_rate == 0.0
    assert result.average_evaluation_score == 0.0


def test_valid_success_is_counted_correctly():

    config = AgentConfig(
        name="Reliable Agent",
        max_attempts=1,
        retry_strategy="none"
    )

    scenario = FailureScenario(
        name="Normal Execution",
        failure_sequence=["none"]
    )

    results = run_benchmark_suite(
        configs=[config],
        scenarios=[scenario]
    )

    result = results[0]

    assert result.successful_executions == 1
    assert result.success_rate == 1.0
    assert result.average_evaluation_score == 1.0


def test_benchmark_records_fixed_backoff():

    config = AgentConfig(
        name="Fixed Retry Agent",
        max_attempts=3,
        retry_strategy="fixed",
        base_delay=0.5
    )

    scenario = FailureScenario(
        name="Two Failures Then Success",
        failure_sequence=["timeout", "rate_limit", "none"]
    )

    results = run_benchmark_suite(
        configs=[config],
        scenarios=[scenario]
    )

    result = results[0]

    assert result.total_retries == 2
    assert result.total_backoff_seconds == 1.0
    assert result.success_rate == 1.0


def test_permanent_failure_can_be_correctly_evaluated():

    config = AgentConfig(
        name="Safe Agent",
        max_attempts=3,
        retry_strategy="exponential",
        base_delay=0.2,
        jitter=False
    )

    scenario = FailureScenario(
        name="Permission Denied",
        failure_sequence=["permission_denied"],
        expected_status="failure"
    )

    results = run_benchmark_suite(
        configs=[config],
        scenarios=[scenario]
    )

    result = results[0]

    assert result.successful_executions == 0
    assert result.success_rate == 0.0
    assert result.average_evaluation_score == 1.0
    assert result.total_retries == 0
