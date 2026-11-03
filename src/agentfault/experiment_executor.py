
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
    """Stores the results of a complete experiment."""

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


def execute_experiment(
    experiment: Experiment,
    fallback_tools: Sequence[Callable[[], ToolResult]] | None = None,
) -> ExperimentExecution:
    """Execute all scenarios in an experiment."""

    experiment.start()

    scenario_results = []

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

    except Exception:
        experiment.fail()
        raise

    total_scenarios = len(scenario_results)

    passed_scenarios = sum(
        result.passed for result in scenario_results
    )

    failed_scenarios = total_scenarios - passed_scenarios

    success_rate = passed_scenarios / total_scenarios

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
