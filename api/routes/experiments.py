
from fastapi import APIRouter, Depends, HTTPException, status

from api.experiment_dependencies import get_experiment_manager

from api.schemas.experiment import (
    ExperimentCreateRequest,
    ExperimentResponse,
    ExperimentExecutionResponse,
    ExecutionTraceResponse,
    ScenarioExecutionResultResponse,
    TraceEventResponse,
)

from agentfault.experiment_manager import ExperimentManager
from agentfault.experiment import Experiment
from agentfault.scenarios import FailureScenario
from agentfault.reliability_config import ReliabilityConfig
from agentfault.experiment_executor import execute_experiment
from api.execution_dependencies import get_execution_results_store

router = APIRouter(
    prefix="/api/v1/experiments",
    tags=["Experiments"],
)


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


@router.post(
    "/{experiment_id}/run",
    response_model=ExperimentExecutionResponse,
)
def run_experiment(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Execute an experiment and store its latest results."""

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

@router.get(
    "/{experiment_id}/results",
    response_model=ExperimentExecutionResponse,
)
def get_experiment_results(
    experiment_id: str,
    manager: ExperimentManager = Depends(get_experiment_manager),
):
    """Retrieve the latest execution results for an experiment."""

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