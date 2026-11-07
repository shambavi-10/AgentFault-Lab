
import pytest

from agentfault.reliability_config import ReliabilityConfig


def test_default_reliability_config():
    config = ReliabilityConfig()

    assert config.max_attempts == 3
    assert config.retry_strategy == "exponential"
    assert config.base_delay == 1.0
    assert config.max_delay == 30.0
    assert config.jitter is True
    assert config.enable_circuit_breaker is False
    assert config.failure_threshold == 3
    assert config.recovery_timeout == 10.0
    assert config.enable_fallback is True


def test_none_retry_strategy_forces_one_attempt():
    config = ReliabilityConfig(
        max_attempts=5,
        retry_strategy="none",
    )

    assert config.max_attempts == 1


def test_fixed_retry_strategy_preserves_attempts():
    config = ReliabilityConfig(
        max_attempts=4,
        retry_strategy="fixed",
    )

    assert config.max_attempts == 4


def test_exponential_retry_strategy_preserves_attempts():
    config = ReliabilityConfig(
        max_attempts=5,
        retry_strategy="exponential",
    )

    assert config.max_attempts == 5


def test_zero_max_attempts_is_rejected():
    with pytest.raises(
        ValueError,
        match="Maximum attempts must be at least 1",
    ):
        ReliabilityConfig(max_attempts=0)


def test_negative_max_attempts_is_rejected():
    with pytest.raises(
        ValueError,
        match="Maximum attempts must be at least 1",
    ):
        ReliabilityConfig(max_attempts=-1)


def test_unsupported_retry_strategy_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unsupported retry strategy",
    ):
        ReliabilityConfig(retry_strategy="random")


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_delay", -1),
        ("max_delay", -1),
    ],
)
def test_negative_retry_delays_are_rejected(field, value):
    with pytest.raises(
        ValueError,
        match="Retry delays cannot be negative",
    ):
        ReliabilityConfig(**{field: value})


def test_failure_threshold_zero_is_rejected():
    with pytest.raises(
        ValueError,
        match="Failure threshold must be at least 1",
    ):
        ReliabilityConfig(failure_threshold=0)


def test_negative_failure_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="Failure threshold must be at least 1",
    ):
        ReliabilityConfig(failure_threshold=-1)


def test_negative_recovery_timeout_is_rejected():
    with pytest.raises(
        ValueError,
        match="Recovery timeout cannot be negative",
    ):
        ReliabilityConfig(recovery_timeout=-1)


def test_zero_recovery_timeout_is_allowed():
    config = ReliabilityConfig(recovery_timeout=0)

    assert config.recovery_timeout == 0
