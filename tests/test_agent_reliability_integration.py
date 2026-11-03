
from agentfault.agent_config import AgentConfig
from agentfault.agent_executor import (
    execute_scenario_with_reliability,
)
from agentfault.models import ToolResult
from agentfault.reliability_config import ReliabilityConfig
from agentfault.scenarios import FailureScenario


def make_success():
    return ToolResult(
        status="success",
        data={"amount": 100}
    )

def test_agent_scenario_uses_unified_engine():
    config = AgentConfig(
        name="Integrated Agent",
        max_attempts=3,
        retry_strategy="exponential",
        base_delay=0,
    )

    scenario = FailureScenario(
        name="Timeout then success",
        failure_sequence=["timeout", "none"],
    )

    execution = execute_scenario_with_reliability(
        config=config,
        scenario=scenario,
    )

    assert execution.result.status == "success"
    assert execution.retry_count == 1
    assert execution.agent_name == "Integrated Agent"


def test_agent_uses_fallback_after_primary_failure():
    config = AgentConfig(
        name="Fallback Agent",
        max_attempts=1,
        retry_strategy="none",
    )

    scenario = FailureScenario(
        name="Primary timeout",
        failure_sequence=["timeout"],
    )

    reliability_config = ReliabilityConfig(
        max_attempts=1,
        retry_strategy="none",
        enable_fallback=True,
    )

    execution = execute_scenario_with_reliability(
        config=config,
        scenario=scenario,
        reliability_config=reliability_config,
        fallback_tools=[make_success],
    )

    assert execution.result.status == "success"
    assert execution.fallback_used is True
    assert execution.fallback_count == 1
    assert execution.valid_business_result is True


def test_agent_uses_circuit_breaker_and_fallback():
    config = AgentConfig(
        name="Circuit Agent",
        max_attempts=2,
        retry_strategy="fixed",
        base_delay=0,
    )

    scenario = FailureScenario(
        name="Repeated timeout",
        failure_sequence=["timeout", "timeout"],
    )

    reliability_config = ReliabilityConfig(
        max_attempts=2,
        retry_strategy="fixed",
        base_delay=0,
        enable_circuit_breaker=True,
        failure_threshold=1,
        recovery_timeout=1000,
    )

    execution = execute_scenario_with_reliability(
        config=config,
        scenario=scenario,
        reliability_config=reliability_config,
        fallback_tools=[make_success],
    )

    assert execution.result.status == "success"
    assert execution.circuit_breaker_enabled is True
    assert execution.fallback_used is True
    assert execution.retry_count == 1


def test_agent_without_fallback_returns_failure():
    config = AgentConfig(
        name="Failure Agent",
        max_attempts=1,
        retry_strategy="none",
    )

    scenario = FailureScenario(
        name="Permanent failure",
        failure_sequence=["permission_denied"],
    )

    execution = execute_scenario_with_reliability(
        config=config,
        scenario=scenario,
    )

    assert execution.result.status == "failure"
    assert execution.fallback_used is False
    assert execution.fallback_count == 0
