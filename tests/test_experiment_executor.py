
import pytest

from agentfault.experiment import Experiment
from agentfault.experiment_executor import (
    ExperimentExecutionError,
    execute_experiment,
)
from agentfault import experiment_executor
from agentfault.models import ToolResult
from agentfault.reliability_config import ReliabilityConfig
from agentfault.scenarios import FailureScenario


def make_scenario(
    name="Timeout recovery",
    sequence=None,
    expected_status="success"
):
    return FailureScenario(
        name=name,
        failure_sequence=sequence or ["timeout", "none"],
        expected_status=expected_status
    )


def make_experiment(scenarios, config=None):
    return Experiment(
        name="Test Experiment",
        scenarios=scenarios,
        reliability_config=config or ReliabilityConfig(
            max_attempts=3,
            retry_strategy="fixed",
            base_delay=0
        )
    )


def make_fallback_success():
    return ToolResult(
        status="success",
        data={"amount": 100}
    )


# BASIC EXPERIMENT EXECUTION

def test_execute_single_scenario():
    experiment = make_experiment([make_scenario()])
    execution = execute_experiment(experiment)

    assert execution.total_scenarios == 1
    assert execution.passed_scenarios == 1
    assert execution.failed_scenarios == 0
    assert execution.success_rate == 1.0
    assert execution.status == "completed"


def test_execute_multiple_scenarios():
    experiment = make_experiment([
        make_scenario("Timeout recovery"),
        make_scenario("Rate limit recovery", ["rate_limit", "none"])
    ])

    execution = execute_experiment(experiment)

    assert execution.total_scenarios == 2
    assert execution.passed_scenarios == 2
    assert execution.failed_scenarios == 0
    assert execution.success_rate == 1.0


def test_execution_stores_experiment_details():
    experiment = make_experiment([make_scenario()])
    execution = execute_experiment(experiment)

    assert execution.experiment_id == experiment.experiment_id
    assert execution.experiment_name == experiment.name
    assert execution.status == "completed"


# EXPECTED FAILURE SCENARIOS

def test_expected_failure_scenario_passes():
    experiment = make_experiment([
        make_scenario(
            name="Permission denied",
            sequence=["permission_denied"],
            expected_status="failure"
        )
    ])

    execution = execute_experiment(experiment)

    assert execution.passed_scenarios == 1
    assert execution.failed_scenarios == 0
    assert execution.scenario_results[0].passed is True


def test_unexpected_failure_scenario_fails():
    experiment = make_experiment([
        make_scenario(
            name="Unexpected permission failure",
            sequence=["permission_denied"],
            expected_status="success"
        )
    ])

    execution = execute_experiment(experiment)

    assert execution.passed_scenarios == 0
    assert execution.failed_scenarios == 1
    assert execution.success_rate == 0.0


def test_malformed_business_response_fails_validation():
    experiment = make_experiment([
        make_scenario(
            name="Malformed response",
            sequence=["malformed"],
            expected_status="success"
        )
    ])

    execution = execute_experiment(experiment)

    assert execution.scenario_results[0].result.status == "success"
    assert execution.scenario_results[0].valid_business_result is False
    assert execution.scenario_results[0].passed is False


# RETRY AND FALLBACK INTEGRATION

def test_experiment_records_retry_count():
    experiment = make_experiment([
        make_scenario(sequence=["timeout", "none"])
    ])

    execution = execute_experiment(experiment)

    assert execution.total_retries == 1
    assert execution.scenario_results[0].retry_count == 1


def test_experiment_uses_fallback():
    config = ReliabilityConfig(
        max_attempts=1,
        retry_strategy="none",
        enable_fallback=True
    )

    experiment = make_experiment(
        [make_scenario(sequence=["timeout"])],
        config=config
    )

    execution = execute_experiment(
        experiment,
        fallback_tools=[make_fallback_success]
    )

    assert execution.passed_scenarios == 1
    assert execution.scenario_results[0].fallback_used is True
    assert execution.scenario_results[0].fallback_count == 1


# EXECUTION METRICS

def test_experiment_records_execution_time():
    experiment = make_experiment([make_scenario()])
    execution = execute_experiment(experiment)

    assert execution.total_execution_time_ms >= 0


def test_experiment_records_scenario_traces():
    experiment = make_experiment([make_scenario()])
    execution = execute_experiment(experiment)

    assert execution.scenario_results[0].trace.count_events(
        "reliability_execution_started"
    ) == 1


# EXPERIMENT LIFECYCLE

def test_experiment_is_completed_after_execution():
    experiment = make_experiment([make_scenario()])

    execute_experiment(experiment)

    assert experiment.status == "completed"


def test_already_started_experiment_cannot_execute_again():
    experiment = make_experiment([make_scenario()])
    experiment.start()

    with pytest.raises(ValueError):
        execute_experiment(experiment)


def test_experiment_handles_fallback_exception():
    experiment = make_experiment([
        make_scenario(sequence=["timeout"])
    ])

    def failing_fallback():
        raise RuntimeError("Fallback infrastructure error")

    config = ReliabilityConfig(
        max_attempts=1,
        retry_strategy="none",
        enable_fallback=True
    )

    experiment.reliability_config = config

    execution = execute_experiment(
        experiment,
        fallback_tools=[failing_fallback]
    )

    assert experiment.status == "completed"
    assert execution.status == "completed"
    assert execution.failed_scenarios == 1
    assert execution.passed_scenarios == 0
    assert execution.scenario_results[0].result.status == "failure"
    assert execution.scenario_results[0].fallback_used is False

def test_unexpected_exception_preserves_partial_execution(
    monkeypatch,
):
    experiment = make_experiment([
        make_scenario(name="First scenario"),
        make_scenario(name="Second scenario"),
    ])

    original_validate_result = experiment_executor.validate_result
    call_count = 0

    def failing_validate_result(result):
        nonlocal call_count
        call_count += 1

        if call_count == 2:
            raise RuntimeError("Unexpected validation error")

        return original_validate_result(result)

    monkeypatch.setattr(
        experiment_executor,
        "validate_result",
        failing_validate_result,
    )

    with pytest.raises(ExperimentExecutionError) as exc_info:
        execute_experiment(experiment)

    error = exc_info.value
    partial_execution = error.execution

    assert experiment.status == "failed"
    assert str(error) == "Unexpected validation error"
    assert isinstance(error.__cause__, RuntimeError)

    assert partial_execution.status == "failed"
    assert partial_execution.total_scenarios == 1
    assert len(partial_execution.scenario_results) == 1
    assert (
        partial_execution.scenario_results[0].scenario_name
        == "First scenario"
    )
