
from agentfault.agent_config import AgentConfig
from agentfault.benchmark_runner import run_benchmark_suite
from agentfault.scenarios import FailureScenario
import pytest

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



def test_repetitions_execute_all_scenarios_multiple_times():

    config = AgentConfig(
        name="Repeated Agent",
        max_attempts=1,
        retry_strategy="none"
    )

    scenarios = [
        FailureScenario(
            name="Normal Execution",
            failure_sequence=["none"]
        ),
        FailureScenario(
            name="Timeout",
            failure_sequence=["timeout"],
            expected_status="failure"
        )
    ]

    results = run_benchmark_suite(
        configs=[config],
        scenarios=scenarios,
        repetitions=3
    )

    result = results[0]

    assert result.total_executions == 6


def test_repeated_execution_aggregates_successes():

    config = AgentConfig(
        name="Success Agent",
        max_attempts=1,
        retry_strategy="none"
    )

    scenario = FailureScenario(
        name="Normal Execution",
        failure_sequence=["none"]
    )

    results = run_benchmark_suite(
        configs=[config],
        scenarios=[scenario],
        repetitions=4
    )

    result = results[0]

    assert result.total_executions == 4
    assert result.successful_executions == 4
    assert result.success_rate == 1.0


def test_repeated_execution_aggregates_retries():

    config = AgentConfig(
        name="Retry Agent",
        max_attempts=3,
        retry_strategy="fixed",
        base_delay=0.5
    )

    scenario = FailureScenario(
        name="Retry Scenario",
        failure_sequence=["timeout", "none"]
    )

    results = run_benchmark_suite(
        configs=[config],
        scenarios=[scenario],
        repetitions=3
    )

    result = results[0]

    assert result.total_executions == 3
    assert result.total_retries == 3
    assert result.total_backoff_seconds == 1.5


def test_zero_repetitions_raises_error():

    config = AgentConfig(
        name="Test Agent",
        max_attempts=1,
        retry_strategy="none"
    )

    scenario = FailureScenario(
        name="Normal Execution",
        failure_sequence=["none"]
    )

    with pytest.raises(ValueError, match="Repetitions must be at least 1"):
        run_benchmark_suite(
            configs=[config],
            scenarios=[scenario],
            repetitions=0
        )


def test_default_repetitions_is_one():

    config = AgentConfig(
        name="Default Agent",
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

    assert results[0].total_executions == 1


def test_empty_agent_configs_raise_error():
    scenario = FailureScenario(
        name="Normal Execution",
        failure_sequence=["none"],
    )

    with pytest.raises(
        ValueError,
        match="At least one agent configuration is required",
    ):
        run_benchmark_suite(
            configs=[],
            scenarios=[scenario],
        )


def test_empty_scenarios_raise_error():
    config = AgentConfig(
        name="Test Agent",
        max_attempts=1,
        retry_strategy="none",
    )

    with pytest.raises(
        ValueError,
        match="At least one scenario is required",
    ):
        run_benchmark_suite(
            configs=[config],
            scenarios=[],
        )
