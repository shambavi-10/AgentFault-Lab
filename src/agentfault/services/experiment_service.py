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
        """Execute an experiment and persist its complete execution history."""

        experiment = self.get_experiment(experiment_id)

        self.repository.update_status(
            self.session,
            experiment_id,
            self.tenant_id,
            "running",
        )

        try:
            execution = execute_experiment(experiment)

        except Exception:
            if experiment.status == "failed":
                self.repository.update_status(
                    self.session,
                    experiment_id,
                    self.tenant_id,
                    "failed",
                )
            raise

        self.repository.update_status(
            self.session,
            experiment_id,
            self.tenant_id,
            execution.status,
        )

        self.execution_repository.save(
            self.session,
            execution,
            self.tenant_id,
        )

        return execution