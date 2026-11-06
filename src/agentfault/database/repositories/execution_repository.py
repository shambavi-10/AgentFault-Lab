import uuid
from datetime import datetime
from typing import Union

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from agentfault.database.models.experiment import ExperimentModel
from agentfault.database.models.experiment_run import ExperimentRunModel
from agentfault.database.models.scenario_execution_result import (
    ScenarioExecutionResultModel,
)
from agentfault.database.models.execution_trace_event import (
    ExecutionTraceEventModel,
)
from agentfault.experiment_executor import ExperimentExecution


class ExecutionRepository:
    """Handles persistent experiment execution history."""

    @staticmethod
    def _to_uuid(value: Union[str, uuid.UUID]) -> uuid.UUID:
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"Invalid UUID: {value}") from exc

    def save(
        self,
        session: Session,
        execution: ExperimentExecution,
        tenant_id: Union[str, uuid.UUID],
    ) -> uuid.UUID:
        """Save an experiment run, scenario results and trace events."""

        experiment_uuid = self._to_uuid(execution.experiment_id)
        tenant_uuid = self._to_uuid(tenant_id)

        experiment = session.scalar(
            select(ExperimentModel).where(
                ExperimentModel.experiment_id == experiment_uuid,
                ExperimentModel.tenant_id == tenant_uuid,
            )
        )

        if experiment is None:
            raise KeyError(
                f"Experiment not found: {execution.experiment_id}"
            )

        run = ExperimentRunModel(
            experiment_id=experiment_uuid,
            status=execution.status,
            total_scenarios=execution.total_scenarios,
            passed_scenarios=execution.passed_scenarios,
            failed_scenarios=execution.failed_scenarios,
            success_rate=execution.success_rate,
            total_execution_time_ms=execution.total_execution_time_ms,
            total_retries=execution.total_retries,
        )

        for position, scenario in enumerate(execution.scenario_results):
            scenario_result = ScenarioExecutionResultModel(
                scenario_name=scenario.scenario_name,
                expected_status=scenario.expected_status,
                result_data=scenario.result.model_dump(mode="json"),
                execution_time_ms=scenario.execution_time_ms,
                retry_count=scenario.retry_count,
                fallback_count=scenario.fallback_count,
                fallback_used=scenario.fallback_used,
                circuit_breaker_enabled=scenario.circuit_breaker_enabled,
                valid_business_result=scenario.valid_business_result,
                passed=scenario.passed,
                position=position,
            )

            for event in scenario.trace.events:
                scenario_result.trace_events.append(
                    ExecutionTraceEventModel(
                        execution_id=event.execution_id,
                        event_type=event.event_type,
                        attempt=event.attempt,
                        status=event.status,
                        error_type=event.error_type,
                        message=event.message,
                        duration_ms=event.duration_ms,
                        timestamp=datetime.fromisoformat(event.timestamp),
                    )
                )

            run.scenario_results.append(scenario_result)

        try:
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.run_id
        except Exception:
            session.rollback()
            raise

    def get_by_id(
        self,
        session: Session,
        run_id: Union[str, uuid.UUID],
        tenant_id: Union[str, uuid.UUID],
    ) -> ExperimentRunModel | None:
        """Retrieve an execution run belonging to a tenant."""

        run_uuid = self._to_uuid(run_id)
        tenant_uuid = self._to_uuid(tenant_id)

        statement = (
            select(ExperimentRunModel)
            .join(ExperimentModel)
            .options(
                selectinload(ExperimentRunModel.scenario_results)
                .selectinload(ScenarioExecutionResultModel.trace_events)
            )
            .where(
                ExperimentRunModel.run_id == run_uuid,
                ExperimentModel.tenant_id == tenant_uuid,
            )
        )

        return session.scalar(statement)

    def list_by_experiment(
        self,
        session: Session,
        experiment_id: Union[str, uuid.UUID],
        tenant_id: Union[str, uuid.UUID],
    ) -> list[ExperimentRunModel]:
        """List execution history for a tenant's experiment."""

        experiment_uuid = self._to_uuid(experiment_id)
        tenant_uuid = self._to_uuid(tenant_id)

        statement = (
            select(ExperimentRunModel)
            .join(ExperimentModel)
            .options(
                selectinload(ExperimentRunModel.scenario_results)
            )
            .where(
                ExperimentRunModel.experiment_id == experiment_uuid,
                ExperimentModel.tenant_id == tenant_uuid,
            )
            .order_by(ExperimentRunModel.created_at.desc())
        )

        return list(session.scalars(statement).all())
