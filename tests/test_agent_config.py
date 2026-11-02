import pytest

from agentfault.agent_config import AgentConfig


def test_create_agent_without_retries():
    agent = AgentConfig(
        name="Agent A",
        max_attempts=1,
        retry_strategy="none"
    )

    assert agent.name == "Agent A"
    assert agent.max_attempts == 1
    assert agent.retry_strategy == "none"


def test_create_agent_with_fixed_retry():
    agent = AgentConfig(
        name="Agent B",
        max_attempts=3,
        retry_strategy="fixed",
        base_delay=0.1
    )

    assert agent.retry_strategy == "fixed"
    assert agent.base_delay == 0.1


def test_create_agent_with_exponential_backoff():
    agent = AgentConfig(
        name="Agent C",
        max_attempts=3,
        retry_strategy="exponential",
        base_delay=0.1,
        max_delay=1.0
    )

    assert agent.retry_strategy == "exponential"
    assert agent.max_delay == 1.0


def test_empty_agent_name_is_rejected():
    with pytest.raises(ValueError):
        AgentConfig("", 1, "none")


def test_zero_attempts_are_rejected():
    with pytest.raises(ValueError):
        AgentConfig("Agent A", 0, "none")


def test_no_retry_agent_cannot_have_multiple_attempts():
    with pytest.raises(ValueError):
        AgentConfig("Agent A", 3, "none")


def test_negative_base_delay_is_rejected():
    with pytest.raises(ValueError):
        AgentConfig("Agent B", 3, "fixed", base_delay=-1)


def test_negative_max_delay_is_rejected():
    with pytest.raises(ValueError):
        AgentConfig("Agent C", 3, "exponential", max_delay=-1)


def test_unsupported_retry_strategy_is_rejected():
    with pytest.raises(ValueError):
        AgentConfig("Agent D", 3, "random")