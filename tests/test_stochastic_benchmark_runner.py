
import pytest

from agentfault.agent_config import AgentConfig
from agentfault.stochastic_benchmark_runner import (
    run_stochastic_benchmark_suite
)


def create_configs():
    return [
        AgentConfig(
            name="No Retry",
            max_attempts=1,
            retry_strategy="none"
        ),
        AgentConfig(
            name="Fixed Retry",
            max_attempts=3,
            retry_strategy="fixed",
            base_delay=1
        ),
        AgentConfig(
            name="Exponential Retry",
            max_attempts=3,
            retry_strategy="exponential",
            base_delay=1
        )
    ]


def test_stochastic_benchmark_rejects_empty_configs():
    with pytest.raises(ValueError):
        run_stochastic_benchmark_suite(configs=[])


def test_stochastic_benchmark_rejects_zero_experiments():
    with pytest.raises(ValueError):
        run_stochastic_benchmark_suite(
            configs=create_configs(),
            experiments=0
        )


def test_stochastic_benchmark_is_reproducible():
    first = run_stochastic_benchmark_suite(
        configs=create_configs(),
        experiments=20,
        timeout_probability=0.3,
        rate_limit_probability=0.2,
        seed=42
    )

    second = run_stochastic_benchmark_suite(
        configs=create_configs(),
        experiments=20,
        timeout_probability=0.3,
        rate_limit_probability=0.2,
        seed=42
    )

    for first_result, second_result in zip(first, second):
        assert first_result.success_rate == second_result.success_rate
        assert first_result.total_retries == second_result.total_retries
        assert (
            first_result.total_backoff_seconds
            == second_result.total_backoff_seconds
        )


def test_stochastic_benchmark_succeeds_without_failures():
    results = run_stochastic_benchmark_suite(
        configs=create_configs(),
        experiments=10,
        timeout_probability=0,
        rate_limit_probability=0,
        seed=42
    )

    for result in results:
        assert result.success_rate == 1.0
        assert result.total_retries == 0


def test_stochastic_benchmark_fails_with_permanent_timeouts():
    results = run_stochastic_benchmark_suite(
        configs=create_configs(),
        experiments=10,
        timeout_probability=1,
        rate_limit_probability=0,
        seed=42
    )

    for result in results:
        assert result.success_rate == 0.0
