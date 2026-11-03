
import pytest

from agentfault.experiment_manager import ExperimentManager
from agentfault.experiment import Experiment
from agentfault.scenarios import FailureScenario


def make_scenario(name="Timeout scenario"):
    return FailureScenario(
        name=name,
        failure_sequence=["timeout", "none"]
    )


def make_experiment(name="Test Experiment"):
    return Experiment(
        name=name,
        scenarios=[make_scenario()]
    )


# --------------------------------------------------
# EXPERIMENT CREATION
# --------------------------------------------------

def test_manager_creates_experiment():
    manager = ExperimentManager()

    experiment = manager.create_experiment(
        name="Retry Experiment",
        scenarios=[make_scenario()],
        description="Testing retry reliability"
    )

    assert experiment.name == "Retry Experiment"
    assert experiment.description == "Testing retry reliability"
    assert experiment.status == "pending"


def test_manager_registers_existing_experiment():
    manager = ExperimentManager()
    experiment = make_experiment()

    registered = manager.register_experiment(experiment)

    assert registered is experiment


def test_manager_rejects_duplicate_experiment():
    manager = ExperimentManager()
    experiment = make_experiment()

    manager.register_experiment(experiment)

    with pytest.raises(ValueError, match="already registered"):
        manager.register_experiment(experiment)


def test_manager_rejects_invalid_experiment_type():
    manager = ExperimentManager()

    with pytest.raises(TypeError, match="Experiment instance"):
        manager.register_experiment("invalid")


# --------------------------------------------------
# EXPERIMENT RETRIEVAL
# --------------------------------------------------

def test_manager_gets_experiment_by_id():
    manager = ExperimentManager()
    experiment = make_experiment()

    manager.register_experiment(experiment)

    retrieved = manager.get_experiment(
        experiment.experiment_id
    )

    assert retrieved is experiment


def test_manager_raises_error_for_unknown_id():
    manager = ExperimentManager()

    with pytest.raises(KeyError, match="Experiment not found"):
        manager.get_experiment("unknown-id")


def test_manager_lists_all_experiments():
    manager = ExperimentManager()

    experiment_a = manager.create_experiment(
        name="Experiment A",
        scenarios=[make_scenario()]
    )

    experiment_b = manager.create_experiment(
        name="Experiment B",
        scenarios=[make_scenario()]
    )

    experiments = manager.list_experiments()

    assert len(experiments) == 2
    assert experiment_a in experiments
    assert experiment_b in experiments


# --------------------------------------------------
# EXPERIMENT LIFECYCLE
# --------------------------------------------------

def test_manager_starts_experiment():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        name="Start Experiment",
        scenarios=[make_scenario()]
    )

    manager.start_experiment(experiment.experiment_id)

    assert experiment.status == "running"


def test_manager_completes_experiment():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        name="Complete Experiment",
        scenarios=[make_scenario()]
    )

    manager.start_experiment(experiment.experiment_id)
    manager.complete_experiment(experiment.experiment_id)

    assert experiment.status == "completed"


def test_manager_fails_experiment():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        name="Failed Experiment",
        scenarios=[make_scenario()]
    )

    manager.start_experiment(experiment.experiment_id)
    manager.fail_experiment(experiment.experiment_id)

    assert experiment.status == "failed"


# --------------------------------------------------
# EXPERIMENT DELETION
# --------------------------------------------------

def test_manager_deletes_pending_experiment():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        name="Delete Experiment",
        scenarios=[make_scenario()]
    )

    manager.delete_experiment(experiment.experiment_id)

    assert manager.list_experiments() == []


def test_manager_cannot_delete_running_experiment():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        name="Running Experiment",
        scenarios=[make_scenario()]
    )

    manager.start_experiment(experiment.experiment_id)

    with pytest.raises(ValueError, match="Only pending"):
        manager.delete_experiment(experiment.experiment_id)


def test_manager_cannot_delete_completed_experiment():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        name="Completed Experiment",
        scenarios=[make_scenario()]
    )

    manager.start_experiment(experiment.experiment_id)
    manager.complete_experiment(experiment.experiment_id)

    with pytest.raises(ValueError, match="Only pending"):
        manager.delete_experiment(experiment.experiment_id)
