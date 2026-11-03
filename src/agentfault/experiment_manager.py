
from agentfault.experiment import Experiment
from agentfault.scenarios import FailureScenario
from agentfault.reliability_config import ReliabilityConfig


class ExperimentManager:
    """Manages experiment creation, registration and lifecycle."""

    def __init__(self):
        self._experiments: dict[str, Experiment] = {}

    def create_experiment(
        self,
        name: str,
        scenarios: list[FailureScenario],
        description: str = "",
        reliability_config: ReliabilityConfig | None = None,
    ) -> Experiment:
        """Create and register a new experiment."""

        experiment = Experiment(
            name=name,
            scenarios=scenarios,
            description=description,
            reliability_config=(
                reliability_config or ReliabilityConfig()
            ),
        )

        self.register_experiment(experiment)

        return experiment

    def register_experiment(
        self,
        experiment: Experiment
    ) -> Experiment:
        """Register an existing experiment."""

        if not isinstance(experiment, Experiment):
            raise TypeError("Expected an Experiment instance")

        experiment_id = experiment.experiment_id

        if experiment_id in self._experiments:
            raise ValueError(
                f"Experiment already registered: {experiment_id}"
            )

        self._experiments[experiment_id] = experiment

        return experiment

    def get_experiment(
        self,
        experiment_id: str
    ) -> Experiment:
        """Retrieve an experiment by its ID."""

        if experiment_id not in self._experiments:
            raise KeyError(
                f"Experiment not found: {experiment_id}"
            )

        return self._experiments[experiment_id]

    def list_experiments(self) -> list[Experiment]:
        """Return all registered experiments."""

        return list(self._experiments.values())

    def start_experiment(
        self,
        experiment_id: str
    ) -> Experiment:
        """Start a registered experiment."""

        experiment = self.get_experiment(experiment_id)
        experiment.start()

        return experiment

    def complete_experiment(
        self,
        experiment_id: str
    ) -> Experiment:
        """Mark a registered experiment as completed."""

        experiment = self.get_experiment(experiment_id)
        experiment.complete()

        return experiment

    def fail_experiment(
        self,
        experiment_id: str
    ) -> Experiment:
        """Mark a registered experiment as failed."""

        experiment = self.get_experiment(experiment_id)
        experiment.fail()

        return experiment

    def delete_experiment(
        self,
        experiment_id: str
    ) -> None:
        """Delete a pending experiment."""

        experiment = self.get_experiment(experiment_id)

        if experiment.status != "pending":
            raise ValueError(
                "Only pending experiments can be deleted"
            )

        del self._experiments[experiment_id]
