import pytest

from agentfault.benchmark_analytics import (
    calculate_benchmark_analytics,
)
from agentfault.benchmark_report import (
    generate_benchmark_report,
    format_benchmark_report,
    BenchmarkReport,
    ScenarioReport,
)
from agentfault.experiment_executor import (
    ExperimentExecution,
    ScenarioExecutionResult,
)
from agentfault.models import ToolResult
from agentfault.tracing import ExecutionTrace
from agentfault.benchmark_report import (
    export_benchmark_report_json,
)

def make_scenario_result(
    name,
    latency,
    passed=True,
    expected_status="success",
    actual_status="success",
    retries=0,
    fallbacks=0,
):
    result = ToolResult(
        status=actual_status,
        data={"amount": 100} if actual_status == "success" else None,
        error="Simulated failure" if actual_status == "failure" else None,
        error_type="timeout" if actual_status == "failure" else None,
        retryable=actual_status == "failure",
    )

    return ScenarioExecutionResult(
        scenario_name=name,
        expected_status=expected_status,
        result=result,
        trace=ExecutionTrace(),
        execution_time_ms=latency,
        retry_count=retries,
        fallback_count=fallbacks,
        fallback_used=fallbacks > 0,
        circuit_breaker_enabled=False,
        valid_business_result=actual_status == "success",
        passed=passed,
    )


def make_execution(results):
    total = len(results)
    passed = sum(item.passed for item in results)

    return ExperimentExecution(
        experiment_id="test-experiment-001",
        experiment_name="Report Test",
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


def make_report():
    execution = make_execution([
        make_scenario_result("Scenario A", 10, retries=1),
        make_scenario_result("Scenario B", 20, retries=0),
        make_scenario_result("Scenario C", 30, retries=2),
    ])

    analytics = calculate_benchmark_analytics(execution)

    return generate_benchmark_report(execution, analytics)


# REPORT GENERATION TESTS

def test_generate_benchmark_report():
    report = make_report()

    assert isinstance(report, BenchmarkReport)
    assert report.experiment_name == "Report Test"
    assert report.experiment_status == "completed"


def test_report_contains_experiment_details():
    report = make_report()

    assert report.experiment_id == "test-experiment-001"
    assert report.experiment_name == "Report Test"


def test_report_contains_scenario_counts():
    report = make_report()

    assert report.total_scenarios == 3
    assert report.passed_scenarios == 3
    assert report.failed_scenarios == 0


def test_report_contains_analytics():
    report = make_report()

    assert report.success_rate == 1.0
    assert report.failure_rate == 0.0
    assert report.average_latency_ms == 20.0
    assert report.minimum_latency_ms == 10.0
    assert report.maximum_latency_ms == 30.0


def test_report_contains_retry_metrics():
    report = make_report()

    assert report.total_retries == 3
    assert report.average_retries == 1.0


def test_report_contains_scenario_details():
    report = make_report()

    assert len(report.scenario_reports) == 3
    assert report.scenario_reports[0].scenario_name == "Scenario A"
    assert report.scenario_reports[0].retry_count == 1


def test_scenario_report_model():
    scenario = ScenarioReport(
        scenario_name="Test Scenario",
        expected_status="success",
        actual_status="success",
        passed=True,
        execution_time_ms=12.5,
        retry_count=1,
        fallback_count=0,
    )

    assert scenario.scenario_name == "Test Scenario"
    assert scenario.passed is True


# VALIDATION TESTS

def test_report_rejects_mismatched_experiment_ids():
    execution = make_execution([
        make_scenario_result("Scenario A", 10),
    ])

    analytics = calculate_benchmark_analytics(execution)
    analytics.experiment_id = "different-experiment"

    with pytest.raises(ValueError, match="IDs do not match"):
        generate_benchmark_report(execution, analytics)


def test_report_rejects_mismatched_experiment_names():
    execution = make_execution([
        make_scenario_result("Scenario A", 10),
    ])

    analytics = calculate_benchmark_analytics(execution)
    analytics.experiment_name = "Different Name"

    with pytest.raises(ValueError, match="names do not match"):
        generate_benchmark_report(execution, analytics)


def test_report_rejects_mismatched_scenario_count():
    execution = make_execution([
        make_scenario_result("Scenario A", 10),
    ])

    analytics = calculate_benchmark_analytics(execution)
    execution.total_scenarios = 2

    with pytest.raises(ValueError, match="Scenario count"):
        generate_benchmark_report(execution, analytics)


# REPORT FORMATTING TESTS

def test_format_benchmark_report_returns_string():
    report = make_report()

    formatted = format_benchmark_report(report)

    assert isinstance(formatted, str)


def test_formatted_report_contains_main_sections():
    formatted = format_benchmark_report(make_report())

    assert "EXPERIMENT DETAILS" in formatted
    assert "OVERALL RESULTS" in formatted
    assert "PERFORMANCE ANALYTICS" in formatted
    assert "RELIABILITY ANALYTICS" in formatted
    assert "SCENARIO DETAILS" in formatted


def test_formatted_report_contains_scenario_names():
    formatted = format_benchmark_report(make_report())

    assert "Scenario A" in formatted
    assert "Scenario B" in formatted
    assert "Scenario C" in formatted


def test_formatted_report_contains_success_rate():
    formatted = format_benchmark_report(make_report())

    assert "Success Rate:     100.00%" in formatted


def test_formatted_report_contains_report_footer():
    formatted = format_benchmark_report(make_report())

    assert "END OF BENCHMARK REPORT" in formatted

# JSON EXPORT TESTS

def test_export_benchmark_report_json_returns_dictionary():
    report = make_report()

    exported = export_benchmark_report_json(report)

    assert isinstance(exported, dict)


def test_json_export_contains_experiment_details():
    report = make_report()

    exported = export_benchmark_report_json(report)

    assert exported["experiment_name"] == "Report Test"
    assert exported["experiment_status"] == "completed"


def test_json_export_contains_analytics():
    report = make_report()

    exported = export_benchmark_report_json(report)

    assert exported["success_rate"] == 1.0
    assert exported["total_retries"] == 3
    assert exported["average_latency_ms"] == 20.0


def test_json_export_contains_scenario_details():
    report = make_report()

    exported = export_benchmark_report_json(report)

    assert len(exported["scenario_reports"]) == 3
    assert exported["scenario_reports"][0]["scenario_name"] == "Scenario A"
    assert exported["scenario_reports"][0]["passed"] is True