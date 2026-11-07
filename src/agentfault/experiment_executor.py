
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from agentfault.experiment import Experiment
from agentfault.models import ToolResult
from agentfault.scenario_runner import ScenarioRunner
from agentfault.faults import validate_result
from agentfault.reliability_engine import ReliabilityEngine
from agentfault.tracing import ExecutionTrace


@dataclass
class ScenarioExecutionResult:
    """Stores the result of one scenario execution."""

    scenario_name: str
    expected_status: str
    result: ToolResult
    trace: ExecutionTrace
    execution_time_ms: float
    retry_count: int
    fallback_count: int
    fallback_used: bool
    circuit_breaker_enabled: bool
    valid_business_result: bool
    passed: bool


@dataclass
class ExperimentExecution:
    """Stores the results of an experiment execution."""

    experiment_id: str
    experiment_name: str
    status: str
    scenario_results: list[ScenarioExecutionResult]
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    success_rate: float
    total_execution_time_ms: float
    total_retries: int


class ExperimentExecutionError(Exception):
    """Execution failure containing partial execution history."""

    def __init__(
        self,
        message: str,
        execution: ExperimentExecution,
    ):
        super().__init__(message)
        self.execution = execution


def build_experiment_execution(
    experiment: Experiment,
    scenario_results: list[ScenarioExecutionResult],
) -> ExperimentExecution:
    """Build execution metrics from completed scenario results."""

    total_scenarios = len(scenario_results)

    passed_scenarios = sum(
        result.passed for result in scenario_results
    )

    failed_scenarios = total_scenarios - passed_scenarios

    success_rate = (
        passed_scenarios / total_scenarios
        if total_scenarios > 0
        else 0.0
    )

    total_execution_time_ms = sum(
        result.execution_time_ms
        for result in scenario_results
    )

    total_retries = sum(
        result.retry_count
        for result in scenario_results
    )

    return ExperimentExecution(
        experiment_id=experiment.experiment_id,
        experiment_name=experiment.name,
        status=experiment.status,
        scenario_results=scenario_results,
        total_scenarios=total_scenarios,
        passed_scenarios=passed_scenarios,
        failed_scenarios=failed_scenarios,
        success_rate=round(success_rate, 4),
        total_execution_time_ms=round(
            total_execution_time_ms, 4
        ),
        total_retries=total_retries,
    )


def execute_experiment(
    experiment: Experiment,
    fallback_tools: Sequence[Callable[[], ToolResult]] | None = None,
) -> ExperimentExecution:
    """Execute all scenarios and preserve partial history on failure."""

    experiment.start()

    scenario_results: list[ScenarioExecutionResult] = []

    try:
        for scenario in experiment.scenarios:
            runner = ScenarioRunner(scenario)

            engine = ReliabilityEngine(
                config=experiment.reliability_config
            )

            execution = engine.execute(
                primary_tool=runner.run,
                fallback_tools=fallback_tools,
            )

            valid_business_result = validate_result(
                execution.result
            )

            if scenario.expected_status == "success":
                passed = (
                    execution.result.status == "success"
                    and valid_business_result
                )
            else:
                passed = (
                    execution.result.status
                    == scenario.expected_status
                )

            scenario_result = ScenarioExecutionResult(
                scenario_name=scenario.name,
                expected_status=scenario.expected_status,
                result=execution.result,
                trace=execution.trace,
                execution_time_ms=execution.execution_time_ms,
                retry_count=execution.retry_count,
                fallback_count=execution.fallback_count,
                fallback_used=execution.fallback_used,
                circuit_breaker_enabled=(
                    execution.circuit_breaker_enabled
                ),
                valid_business_result=valid_business_result,
                passed=passed,
            )

            scenario_results.append(scenario_result)

        experiment.complete()

    except Exception as exc:
        experiment.fail()

        partial_execution = build_experiment_execution(
            experiment,
            scenario_results,
        )

        raise ExperimentExecutionError(
            str(exc),
            partial_execution,
        ) from exc

    return build_experiment_execution(
        experiment,
        scenario_results,
    )
