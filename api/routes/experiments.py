
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_report_manager
from api.experiment_dependencies import get_experiment_manager
from api.execution_dependencies import get_execution_results_store

from api.schemas.experiment import (
    ExperimentCreateRequest,
    ExperimentResponse,
    ExperimentExecutionResponse,
    ExecutionTraceResponse,
    ScenarioExecutionResultResponse,
    TraceEventResponse,
    ExperimentComparisonRequest,
    ExperimentComparisonResponse,
    StrategyComparisonResponse,
    BenchmarkAnalyticsResponse,
    BenchmarkReportResponse,
)

from agentfault.experiment_manager import ExperimentManager
from agentfault.experiment import Experiment
from agentfault.scenarios import FailureScenario
from agentfault.reliability_config import ReliabilityConfig

from agentfault.experiment_executor import (
    execute_experiment,
    ExperimentExecution,
    ScenarioExecutionResult,
)

from agentfault.experiment_comparator import compare_experiments
from agentfault.benchmark_analytics import calculate_benchmark_analytics
from agentfault.benchmark_report import (
    generate_benchmark_report,
    export_benchmark_report_json,
)
from agentfault.report_manager import ReportManager

from agentfault.models import ToolResult
from agentfault.tracing import ExecutionTrace, TraceEvent


router = APIRouter(
    prefix="/api/v1/experiments",
    tags=["Experiments"],
)


# --------------------------------------------------
# Conversion helpers
# --------------------------------------------------

def convert_experiment(experiment: Experiment) -> ExperimentResponse:
    """Convert an Experiment object into an API response."""

    return ExperimentResponse(
        experiment_id=experiment.experiment_id,
        name=experiment.name,
        description=experiment.description,
        status=experiment.status,
        created_at=experiment.created_at,
        scenarios=[
            {
                "name": scenario.name,
                "failure_sequence": scenario.failure_sequence,
                "expected_status": scenario.expected_status,
            }
            for scenario in experiment.scenarios
        ],
        reliability_config=experiment.reliability_config.__dict__,
    )


def convert_execution_response(
    response: ExperimentExecutionResponse,
) -> ExperimentExecution:
    """Convert an API execution response into the engine dataclass."""

    scenario_results = []

    for result in response.scenario_results:
        trace = ExecutionTrace(
            execution_id=result.trace.execution_id,
            events=[
                TraceEvent(**event.model_dump())
                for event in result.trace.events
            ],
        )

        scenario_results.append(
            ScenarioExecutionResult(
                scenario_name=result.scenario_name,
                expected_status=result.expected_status,
                result=ToolResult(**result.result),
                trace=trace,
                execution_time_ms=result.execution_time_ms,
                retry_count=result.retry_count,
                fallback_count=result.fallback_count,
                fallback_used=result.fallback_used,
                circuit_breaker_enabled=result.circuit_breaker_enabled,
                valid_business_result=result.valid_business_result,
                passed=result.passed,
            )
        )

    return ExperimentExecution(
        experiment_id=response.experiment_id,
        experiment_name=response.experiment_name,
        status=response.status,
        scenario_results=scenario_results,
        total_scenarios=response.total_scenarios,
        passed_scenarios=response.passed_scenarios,
        failed_scenarios=response.failed_scenarios,
        success_rate=response.success_rate,
        total_execution_time_ms=response.total_execution_time_ms,
        total_retries=response.total_retries,
    )


# --------------------------------------------------
# Experiment management APIs
# --------------------------------------------------

@router.post(
    "",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(
    request: ExperimentCreateRequest,
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Create and register a new experiment."""

    try:
        scenarios = [
            FailureScenario(**scenario.model_dump())
            for scenario in request.scenarios
        ]

        config = ReliabilityConfig(
            **request.reliability_config.model_dump()
        )

        experiment = manager.create_experiment(
            name=request.name,
            description=request.description,
            scenarios=scenarios,
            reliability_config=config,
        )

        return convert_experiment(experiment)

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[ExperimentResponse],
)
def list_experiments(
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Return all registered experiments."""

    return [
        convert_experiment(experiment)
        for experiment in manager.list_experiments()
    ]


@router.get(
    "/{experiment_id}",
    response_model=ExperimentResponse,
)
def get_experiment(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Retrieve one experiment by ID."""

    try:
        experiment = manager.get_experiment(experiment_id)
        return convert_experiment(experiment)

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{experiment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_experiment(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Delete a pending experiment."""

    try:
        manager.delete_experiment(experiment_id)

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Experiment execution API
# --------------------------------------------------

@router.post(
    "/{experiment_id}/run",
    response_model=ExperimentExecutionResponse,
)
def run_experiment(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Execute an experiment and store its results."""

    try:
        experiment = manager.get_experiment(experiment_id)
        execution = execute_experiment(experiment)

        response = ExperimentExecutionResponse(
            experiment_id=execution.experiment_id,
            experiment_name=execution.experiment_name,
            status=execution.status,
            scenario_results=[
                ScenarioExecutionResultResponse(
                    scenario_name=result.scenario_name,
                    expected_status=result.expected_status,
                    result=result.result.model_dump(),
                    trace=ExecutionTraceResponse(
                        execution_id=result.trace.execution_id,
                        events=[
                            TraceEventResponse(**event)
                            for event in result.trace.get_events()
                        ],
                    ),
                    execution_time_ms=result.execution_time_ms,
                    retry_count=result.retry_count,
                    fallback_count=result.fallback_count,
                    fallback_used=result.fallback_used,
                    circuit_breaker_enabled=result.circuit_breaker_enabled,
                    valid_business_result=result.valid_business_result,
                    passed=result.passed,
                )
                for result in execution.scenario_results
            ],
            total_scenarios=execution.total_scenarios,
            passed_scenarios=execution.passed_scenarios,
            failed_scenarios=execution.failed_scenarios,
            success_rate=execution.success_rate,
            total_execution_time_ms=execution.total_execution_time_ms,
            total_retries=execution.total_retries,
        )

        results_store = get_execution_results_store()

        if experiment_id not in results_store:
            results_store[experiment_id] = []

        results_store[experiment_id].append(response)

        return response

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Experiment results API
# --------------------------------------------------

@router.get(
    "/{experiment_id}/results",
    response_model=ExperimentExecutionResponse,
)
def get_experiment_results(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Retrieve the latest execution results."""

    try:
        manager.get_experiment(experiment_id)

        results_store = get_execution_results_store()
        execution_history = results_store.get(experiment_id, [])

        if not execution_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No execution results found for this experiment",
            )

        return execution_history[-1]

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{experiment_id}/history",
    response_model=list[ExperimentExecutionResponse],
)
def get_experiment_history(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Retrieve all execution records for an experiment."""

    try:
        manager.get_experiment(experiment_id)

        results_store = get_execution_results_store()
        execution_history = results_store.get(experiment_id, [])

        return execution_history

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Experiment comparison API
# --------------------------------------------------

@router.post(
    "/compare",
    response_model=ExperimentComparisonResponse,
)
def compare_experiment_strategies(
    request: ExperimentComparisonRequest,
):
    """Compare multiple reliability strategies."""

    try:
        scenarios = [
            FailureScenario(**scenario.model_dump())
            for scenario in request.scenarios
        ]

        strategies = {
            name: ReliabilityConfig(**config.model_dump())
            for name, config in request.strategies.items()
        }

        comparison = compare_experiments(
            scenarios=scenarios,
            strategies=strategies,
        )

        return ExperimentComparisonResponse(
            comparisons=[
                StrategyComparisonResponse(
                    strategy_name=item.strategy_name,
                    experiment_execution=ExperimentExecutionResponse(
                        experiment_id=item.experiment_execution.experiment_id,
                        experiment_name=item.experiment_execution.experiment_name,
                        status=item.experiment_execution.status,
                        scenario_results=[
                            ScenarioExecutionResultResponse(
                                scenario_name=result.scenario_name,
                                expected_status=result.expected_status,
                                result=result.result.model_dump(),
                                trace=ExecutionTraceResponse(
                                    execution_id=result.trace.execution_id,
                                    events=[
                                        TraceEventResponse(**event)
                                        for event in result.trace.get_events()
                                    ],
                                ),
                                execution_time_ms=result.execution_time_ms,
                                retry_count=result.retry_count,
                                fallback_count=result.fallback_count,
                                fallback_used=result.fallback_used,
                                circuit_breaker_enabled=result.circuit_breaker_enabled,
                                valid_business_result=result.valid_business_result,
                                passed=result.passed,
                            )
                            for result in item.experiment_execution.scenario_results
                        ],
                        total_scenarios=item.experiment_execution.total_scenarios,
                        passed_scenarios=item.experiment_execution.passed_scenarios,
                        failed_scenarios=item.experiment_execution.failed_scenarios,
                        success_rate=item.experiment_execution.success_rate,
                        total_execution_time_ms=item.experiment_execution.total_execution_time_ms,
                        total_retries=item.experiment_execution.total_retries,
                    ),
                    success_rate=item.success_rate,
                    average_execution_time_ms=item.average_execution_time_ms,
                    total_retries=item.total_retries,
                    total_fallbacks=item.total_fallbacks,
                    passed_scenarios=item.passed_scenarios,
                    failed_scenarios=item.failed_scenarios,
                )
                for item in comparison.comparisons
            ],
            best_strategy=comparison.best_strategy,
            total_strategies=comparison.total_strategies,
        )

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Benchmark analytics API
# --------------------------------------------------

@router.get(
    "/{experiment_id}/analytics",
    response_model=BenchmarkAnalyticsResponse,
)
def get_experiment_analytics(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Retrieve benchmark analytics for the latest execution."""

    try:
        manager.get_experiment(experiment_id)

        results_store = get_execution_results_store()
        execution_history = results_store.get(experiment_id, [])

        if not execution_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No execution results found for this experiment",
            )

        latest_execution = convert_execution_response(
            execution_history[-1]
        )

        analytics = calculate_benchmark_analytics(latest_execution)

        return BenchmarkAnalyticsResponse(**analytics.__dict__)

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Benchmark report generation API
# --------------------------------------------------

@router.post(
    "/{experiment_id}/report",
    response_model=BenchmarkReportResponse,
)
def generate_experiment_report(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
    report_manager: ReportManager = Depends(get_report_manager),
):
    """Generate and persist a benchmark report."""

    try:
        manager.get_experiment(experiment_id)

        results_store = get_execution_results_store()
        execution_history = results_store.get(experiment_id, [])

        if not execution_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No execution results found for this experiment",
            )

        execution = convert_execution_response(
            execution_history[-1]
        )

        analytics = calculate_benchmark_analytics(execution)

        report = generate_benchmark_report(
            execution=execution,
            analytics=analytics,
        )

        report_manager.storage.save_report(report)

        return BenchmarkReportResponse(
            **export_benchmark_report_json(report)
        )

    except HTTPException:
        raise

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate benchmark report",
        ) from exc


# --------------------------------------------------
# Benchmark report retrieval API
# --------------------------------------------------

@router.get(
    "/{experiment_id}/report",
    response_model=BenchmarkReportResponse,
)
def get_experiment_report(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
    report_manager: ReportManager = Depends(get_report_manager),
):
    """Retrieve a saved benchmark report."""

    try:
        manager.get_experiment(experiment_id)

        report = report_manager.get_report(experiment_id)

        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benchmark report not found",
            )

        return BenchmarkReportResponse(**report)

    except HTTPException:
        raise

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Benchmark report JSON export API
# --------------------------------------------------

@router.get(
    "/{experiment_id}/report/json",
)
def export_experiment_report_json(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
    report_manager: ReportManager = Depends(get_report_manager),
):
    """Export a saved benchmark report as JSON."""

    try:
        manager.get_experiment(experiment_id)

        report = report_manager.get_report(experiment_id)

        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benchmark report not found",
            )

        # The stored report is already a JSON-compatible dictionary.
        return report

    except HTTPException:
        raise

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
