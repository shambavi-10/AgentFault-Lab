
import pytest

from agentfault.benchmark_analytics import (
    calculate_percentile,
    calculate_benchmark_analytics,
)
from agentfault.experiment_executor import (
    ExperimentExecution,
    ScenarioExecutionResult,
)
from agentfault.models import ToolResult
from agentfault.tracing import ExecutionTrace


def make_scenario_result(
    name,
    latency,
    passed=True,
    retries=0,
    fallbacks=0,
    fallback_used=False,
):
    result = ToolResult(
        status="success",
        data={"amount": 100},
    )

    return ScenarioExecutionResult(
        scenario_name=name,
        expected_status="success",
        result=result,
        trace=ExecutionTrace(),
        execution_time_ms=latency,
        retry_count=retries,
        fallback_count=fallbacks,
        fallback_used=fallback_used,
        circuit_breaker_enabled=False,
        valid_business_result=True,
        passed=passed,
    )


def make_execution(results):
    total = len(results)
    passed = sum(item.passed for item in results)

    return ExperimentExecution(
        experiment_id="test-experiment-001",
        experiment_name="Analytics Test",
        status="completed",
        scenario_results=results,
        total_scenarios=total,
        passed_scenarios=passed,
        failed_scenarios=total - passed,
        success_rate=passed / total if total else 0,
        total_execution_time_ms=sum(
            item.execution_time_ms for item in results
        ),
        total_retries=sum(item.retry_count for item in results),
    )


# PERCENTILE TESTS

def test_calculate_p50():
    assert calculate_percentile(
        [10, 20, 30, 40, 50], 50
    ) == 30


def test_calculate_p90():
    assert calculate_percentile(
        [10, 20, 30, 40, 50], 90
    ) == 50


def test_calculate_p95():
    assert calculate_percentile(
        [10, 20, 30, 40, 50], 95
    ) == 50


def test_calculate_p99():
    assert calculate_percentile(
        [10, 20, 30, 40, 50], 99
    ) == 50


def test_percentile_rejects_empty_values():
    with pytest.raises(ValueError):
        calculate_percentile([], 50)


def test_percentile_rejects_invalid_percentile():
    with pytest.raises(ValueError):
        calculate_percentile([10, 20], 0)


def test_percentile_rejects_negative_values():
    with pytest.raises(ValueError):
        calculate_percentile([10, -5, 20], 50)


# LATENCY ANALYTICS TESTS

def test_calculate_average_latency():
    execution = make_execution([
        make_scenario_result("A", 10),
        make_scenario_result("B", 20),
        make_scenario_result("C", 30),
    ])

    analytics = calculate_benchmark_analytics(execution)

    assert analytics.average_latency_ms == 20


def test_calculate_minimum_latency():
    execution = make_execution([
        make_scenario_result("A", 10),
        make_scenario_result("B", 20),
        make_scenario_result("C", 30),
    ])

    analytics = calculate_benchmark_analytics(execution)

    assert analytics.minimum_latency_ms == 10


def test_calculate_maximum_latency():
    execution = make_execution([
        make_scenario_result("A", 10),
        make_scenario_result("B", 20),
        make_scenario_result("C", 30),
    ])

    analytics = calculate_benchmark_analytics(execution)

    assert analytics.maximum_latency_ms == 30


# RELIABILITY ANALYTICS TESTS

def test_calculate_success_and_failure_rates():
    execution = make_execution([
        make_scenario_result("A", 10, passed=True),
        make_scenario_result("B", 20, passed=True),
        make_scenario_result("C", 30, passed=False),
        make_scenario_result("D", 40, passed=True),
    ])

    analytics = calculate_benchmark_analytics(execution)

    assert analytics.success_rate == 0.75
    assert analytics.failure_rate == 0.25
    assert analytics.passed_scenarios == 3
    assert analytics.failed_scenarios == 1


# RETRY AND FALLBACK ANALYTICS TESTS

def test_calculate_retry_metrics():
    execution = make_execution([
        make_scenario_result("A", 10, retries=2),
        make_scenario_result("B", 20, retries=1),
        make_scenario_result("C", 30, retries=0),
    ])

    analytics = calculate_benchmark_analytics(execution)

    assert analytics.total_retries == 3
    assert analytics.average_retries == 1


def test_calculate_fallback_metrics():
    execution = make_execution([
        make_scenario_result(
            "A", 10, fallbacks=1, fallback_used=True
        ),
        make_scenario_result(
            "B", 20, fallbacks=2, fallback_used=True
        ),
        make_scenario_result(
            "C", 30, fallbacks=0, fallback_used=False
        ),
        make_scenario_result(
            "D", 40, fallbacks=1, fallback_used=False
        ),
    ])

    analytics = calculate_benchmark_analytics(execution)

    assert analytics.total_fallbacks == 4
    assert analytics.fallback_usage_rate == 0.5


# INPUT VALIDATION TESTS

def test_analytics_rejects_empty_execution():
    execution = make_execution([])

    with pytest.raises(ValueError):
        calculate_benchmark_analytics(execution)


def test_analytics_rejects_mismatched_scenario_count():
    execution = make_execution([
        make_scenario_result("A", 10),
        make_scenario_result("B", 20),
    ])

    execution.total_scenarios = 3

    with pytest.raises(ValueError):
        calculate_benchmark_analytics(execution)


def test_analytics_rejects_negative_latency():
    execution = make_execution([
        make_scenario_result("A", -10),
    ])

    with pytest.raises(ValueError):
        calculate_benchmark_analytics(execution)
