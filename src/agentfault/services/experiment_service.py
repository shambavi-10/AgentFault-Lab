
from sqlalchemy.orm import Session

from agentfault.database.repositories.experiment_repository import (
    ExperimentRepository,
)
from agentfault.database.repositories.execution_repository import (
    ExecutionRepository,
)
from agentfault.experiment import Experiment
from agentfault.experiment_executor import (
    ExperimentExecution,
    ExperimentExecutionError,
    build_experiment_execution,
    execute_experiment,
)
from agentfault.reliability_config import ReliabilityConfig
from agentfault.scenarios import FailureScenario


class ExperimentService:
    """Coordinates experiment operations and database persistence."""

    def __init__(
        self,
        session: Session,
        tenant_id: str,
        repository: ExperimentRepository | None = None,
        execution_repository: ExecutionRepository | None = None,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.repository = repository or ExperimentRepository()
        self.execution_repository = (
            execution_repository or ExecutionRepository()
        )

    def create_experiment(
        self,
        name: str,
        scenarios: list[FailureScenario],
        description: str = "",
        reliability_config: ReliabilityConfig | None = None,
    ) -> Experiment:
        """Create and persist a new experiment."""

        experiment = Experiment(
            name=name,
            scenarios=scenarios,
            description=description,
            reliability_config=reliability_config or ReliabilityConfig(),
        )

        return self.repository.create(
            self.session,
            experiment,
            self.tenant_id,
        )

    def list_experiments(self) -> list[Experiment]:
        """List experiments belonging to this tenant."""

        return self.repository.list_by_tenant(
            self.session,
            self.tenant_id,
        )

    def get_experiment(self, experiment_id: str) -> Experiment:
        """Retrieve one experiment belonging to this tenant."""

        experiment = self.repository.get_by_id(
            self.session,
            experiment_id,
            self.tenant_id,
        )

        if experiment is None:
            raise KeyError(f"Experiment not found: {experiment_id}")

        return experiment

    def delete_experiment(self, experiment_id: str) -> None:
        """Delete a pending experiment."""

        self.repository.delete_pending(
            self.session,
            experiment_id,
            self.tenant_id,
        )

    def run_experiment(
        self,
        experiment_id: str,
    ) -> ExperimentExecution:
        """Execute an experiment and persist complete or partial history."""

        experiment = self.get_experiment(experiment_id)

        self.repository.update_status(
            self.session,
            experiment_id,
            self.tenant_id,
            "running",
        )

        try:
            execution = execute_experiment(experiment)

        except ExperimentExecutionError as exc:
            # Mark the experiment as failed.
            self.repository.update_status(
                self.session,
                experiment_id,
                self.tenant_id,
                "failed",
            )

            # Persist completed scenarios and their trace events.
            self.execution_repository.save(
                self.session,
                exc.execution,
                self.tenant_id,
            )

            # Re-raise the original execution exception.
            if exc.__cause__ is not None:
                raise exc.__cause__ from exc

            raise

        except Exception:
            # Handle unexpected failures outside the executor's
            # dedicated exception handling.
            if experiment.status == "failed":
                self.repository.update_status(
                    self.session,
                    experiment_id,
                    self.tenant_id,
                    "failed",
                )

                # Persist a failed run even when no scenario completed.
                failed_execution = build_experiment_execution(
                    experiment,
                    [],
                )

                self.execution_repository.save(
                    self.session,
                    failed_execution,
                    self.tenant_id,
                )

            raise

        # Persist the final experiment status.
        self.repository.update_status(
            self.session,
            experiment_id,
            self.tenant_id,
            execution.status,
        )

        # Persist the complete execution history.
        self.execution_repository.save(
            self.session,
            execution,
            self.tenant_id,
        )

        return execution
