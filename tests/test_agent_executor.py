from agentfault.agent_config import AgentConfig
from agentfault.agent_executor import execute_scenario
from agentfault.scenarios import FailureScenario


def test_agent_executor_runs_scenario_successfully():

    config = AgentConfig(
        name="Agent A",
        max_attempts=3,
        retry_strategy="exponential",
        base_delay=0,
        jitter=False
    )

    scenario = FailureScenario(
        name="Timeout then success",
        failure_sequence=["timeout", "none"]
    )

    execution = execute_scenario(config, scenario)

    assert execution.agent_name == "Agent A"
    assert execution.scenario_name == "Timeout then success"
    assert execution.result.status == "success"
    assert execution.retry_count == 1
    assert execution.execution_time_ms >= 0


def test_agent_without_retries_fails_on_timeout():

    config = AgentConfig(
        name="Agent B",
        max_attempts=1,
        retry_strategy="none"
    )

    scenario = FailureScenario(
        name="Timeout scenario",
        failure_sequence=["timeout", "none"]
    )

    execution = execute_scenario(config, scenario)

    assert execution.result.status == "failure"
    assert execution.retry_count == 0


def test_agent_executor_records_trace():

    config = AgentConfig(
        name="Agent C",
        max_attempts=3,
        retry_strategy="fixed",
        base_delay=0
    )

    scenario = FailureScenario(
        name="Two failures then success",
        failure_sequence=["timeout", "rate_limit", "none"]
    )

    execution = execute_scenario(config, scenario)

    assert execution.result.status == "success"
    assert execution.retry_count == 2
    assert execution.trace.count_events("execution_started") == 1
    assert execution.trace.count_events("execution_completed") == 1


def test_malformed_output_is_not_valid_business_success():

    config = AgentConfig(
        name="Agent Malformed",
        max_attempts=1,
        retry_strategy="none"
    )

    scenario = FailureScenario(
        name="Malformed response",
        failure_sequence=["malformed"],
        expected_status="success"
    )

    execution = execute_scenario(config, scenario)

    assert execution.result.status == "success"
    assert execution.valid_business_result is False


def test_fixed_retry_records_scheduled_backoff():

    config = AgentConfig(
        name="Agent Fixed",
        max_attempts=3,
        retry_strategy="fixed",
        base_delay=0.5
    )

    scenario = FailureScenario(
        name="Two failures then success",
        failure_sequence=["timeout", "rate_limit", "none"]
    )

    execution = execute_scenario(config, scenario)

    assert execution.result.status == "success"
    assert execution.retry_count == 2
    assert execution.scheduled_backoff_seconds == 1.0
