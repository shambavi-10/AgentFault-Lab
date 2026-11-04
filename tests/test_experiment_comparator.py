
import pytest

from agentfault.experiment_comparator import compare_experiments
from agentfault.models import ToolResult
from agentfault.reliability_config import ReliabilityConfig
from agentfault.scenarios import FailureScenario


def make_scenarios():
    return [
        FailureScenario(
            name="Timeout recovery",
            failure_sequence=["timeout", "none"],
            expected_status="success",
        ),
        FailureScenario(
            name="Rate limit recovery",
            failure_sequence=["rate_limit", "none"],
            expected_status="success",
        ),
        FailureScenario(
            name="Permission denied",
            failure_sequence=["permission_denied"],
            expected_status="failure",
        ),
    ]


def make_strategies():
    return {
        "No Retry": ReliabilityConfig(
            max_attempts=1,
            retry_strategy="none",
            enable_fallback=False,
        ),
        "Exponential Retry": ReliabilityConfig(
            max_attempts=3,
            retry_strategy="exponential",
            base_delay=0,
            jitter=False,
            enable_fallback=False,
        ),
    }


def make_fallback_success():
    return ToolResult(
        status="success",
        data={"amount": 100},
    )


# BASIC COMPARISON TESTS

def test_compare_multiple_strategies():
    comparison = compare_experiments(
        scenarios=make_scenarios(),
        strategies=make_strategies(),
    )

    assert comparison.total_strategies == 2
    assert len(comparison.comparisons) == 2


def test_comparison_contains_strategy_names():
    comparison = compare_experiments(
        scenarios=make_scenarios(),
        strategies=make_strategies(),
    )

    names = [
        item.strategy_name
        for item in comparison.comparisons
    ]

    assert names == ["No Retry", "Exponential Retry"]


def test_retry_strategy_has_higher_success_rate():
    comparison = compare_experiments(
        scenarios=make_scenarios(),
        strategies=make_strategies(),
    )

    no_retry = comparison.comparisons[0]
    retry = comparison.comparisons[1]

    assert retry.success_rate > no_retry.success_rate


def test_comparison_records_retry_counts():
    comparison = compare_experiments(
        scenarios=make_scenarios(),
        strategies=make_strategies(),
    )

    no_retry = comparison.comparisons[0]
    retry = comparison.comparisons[1]

    assert no_retry.total_retries == 0
    assert retry.total_retries > 0


# METRICS TESTS

def test_comparison_records_execution_time():
    comparison = compare_experiments(
        scenarios=make_scenarios(),
        strategies=make_strategies(),
    )

    for item in comparison.comparisons:
        assert item.average_execution_time_ms >= 0


def test_comparison_records_scenario_counts():
    comparison = compare_experiments(
        scenarios=make_scenarios(),
        strategies=make_strategies(),
    )

    for item in comparison.comparisons:
        assert item.passed_scenarios + item.failed_scenarios == 3


def test_comparison_identifies_best_strategy():
    comparison = compare_experiments(
        scenarios=make_scenarios(),
        strategies=make_strategies(),
    )

    assert comparison.best_strategy == "Exponential Retry"


# FALLBACK TESTS

def test_comparison_supports_fallback_strategy():
    strategies = {
        "No Fallback": ReliabilityConfig(
            max_attempts=1,
            retry_strategy="none",
            enable_fallback=False,
        ),
        "With Fallback": ReliabilityConfig(
            max_attempts=1,
            retry_strategy="none",
            enable_fallback=True,
        ),
    }

    scenarios = [
        FailureScenario(
            name="Timeout scenario",
            failure_sequence=["timeout"],
            expected_status="success",
        )
    ]

    comparison = compare_experiments(
        scenarios=scenarios,
        strategies=strategies,
        fallback_tools=[make_fallback_success],
    )

    without_fallback = comparison.comparisons[0]
    with_fallback = comparison.comparisons[1]

    assert without_fallback.success_rate == 0.0
    assert with_fallback.success_rate == 1.0
    assert with_fallback.total_fallbacks == 1


# INPUT VALIDATION TESTS

def test_comparison_rejects_empty_scenarios():
    with pytest.raises(ValueError):
        compare_experiments(
            scenarios=[],
            strategies=make_strategies(),
        )


def test_comparison_rejects_empty_strategies():
    with pytest.raises(ValueError):
        compare_experiments(
            scenarios=make_scenarios(),
            strategies={},
        )


def test_comparison_rejects_empty_strategy_name():
    with pytest.raises(ValueError):
        compare_experiments(
            scenarios=make_scenarios(),
            strategies={
                "": ReliabilityConfig()
            },
        )


def test_comparison_rejects_invalid_configuration_type():
    with pytest.raises(TypeError):
        compare_experiments(
            scenarios=make_scenarios(),
            strategies={
                "Invalid": "not a reliability config"
            },
        )
