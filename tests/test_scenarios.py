import pytest

from agentfault.scenarios import FailureScenario
from agentfault.scenario_runner import ScenarioRunner
from agentfault.retry import run_with_retry
from agentfault.tracing import ExecutionTrace

def test_scenario_runs_timeout_then_success():
    scenario = FailureScenario(
        name="timeout_recovery",
        failure_sequence=["timeout", "none"]
    )

    runner = ScenarioRunner(scenario)

    first_result = runner.run()
    second_result = runner.run()

    assert first_result.status == "failure"
    assert first_result.error_type == "timeout"

    assert second_result.status == "success"
    assert second_result.data == {"amount": 100}

def test_scenario_runs_multiple_failures():
    scenario = FailureScenario(
        name="multiple_timeouts",
        failure_sequence=["timeout", "timeout", "none"]
    )

    runner = ScenarioRunner(scenario)

    first = runner.run()
    second = runner.run()
    third = runner.run()

    assert first.error_type == "timeout"
    assert second.error_type == "timeout"
    assert third.status == "success"

def test_invalid_scenario_outcome_is_rejected():
    with pytest.raises(ValueError):
        FailureScenario(
            name="invalid_scenario",
            failure_sequence=["timeot"]
        )


def test_empty_scenario_name_is_rejected():
    with pytest.raises(ValueError):
        FailureScenario(
            name="",
            failure_sequence=["success"]
        )

from agentfault.retry import run_with_retry
from agentfault.tracing import ExecutionTrace


def test_scenario_integrates_with_retry_engine():
    scenario = FailureScenario(
        name="automatic_recovery",
        failure_sequence=["timeout", "timeout", "none"]
    )

    runner = ScenarioRunner(scenario)
    trace = ExecutionTrace()

    result = run_with_retry(
        tool_call=runner.run,
        max_attempts=3,
        base_delay=0,
        jitter=False,
        sleep_fn=lambda delay: None,
        trace=trace
    )

    assert result.status == "success"
    assert runner.current_attempt == 3
    assert trace.count_events("retry_scheduled") == 2
    assert trace.count_events("execution_completed") == 1

def test_scenario_stops_on_permanent_failure():
    scenario = FailureScenario(
        name="permission_failure",
        failure_sequence=["permission_denied", "none"]
    )

    runner = ScenarioRunner(scenario)
    trace = ExecutionTrace()

    result = run_with_retry(
        tool_call=runner.run,
        max_attempts=3,
        base_delay=0,
        jitter=False,
        sleep_fn=lambda delay: None,
        trace=trace
    )

    assert result.status == "failure"
    assert result.error_type == "permission_denied"
    assert runner.current_attempt == 1
    assert trace.count_events("retry_scheduled") == 0
    assert trace.count_events("execution_completed") == 1

def test_scenario_runner_raises_when_sequence_is_exhausted():
    scenario = FailureScenario(
        name="Single outcome",
        failure_sequence=["timeout"]
    )

    runner = ScenarioRunner(scenario)

    first_result = runner.run()

    assert first_result.status == "failure"
    assert first_result.error_type == "timeout"

    import pytest

    with pytest.raises(RuntimeError, match="Scenario sequence exhausted"):
        runner.run()

def test_empty_failure_sequence_is_rejected():
    with pytest.raises(
        ValueError,
        match="Failure sequence cannot be empty"
    ):
        FailureScenario(
            name="empty_sequence",
            failure_sequence=[]
        )

def test_invalid_expected_status_is_rejected():
    with pytest.raises(
        ValueError,
        match="Invalid expected status"
    ):
        FailureScenario(
            name="invalid_status",
            failure_sequence=["timeout"],
            expected_status="pending"
        )