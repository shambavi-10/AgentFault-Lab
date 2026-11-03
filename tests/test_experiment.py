
import pytest

from agentfault.experiment import Experiment
from agentfault.scenarios import FailureScenario


def make_scenario(name="Timeout scenario"):
    return FailureScenario(
        name=name,
        failure_sequence=["timeout", "none"]
    )


# --------------------------------------------------
# EXPERIMENT CREATION TESTS
# --------------------------------------------------

def test_experiment_creation():
    experiment = Experiment(
        name="Retry Experiment",
        scenarios=[make_scenario()]
    )

    assert experiment.name == "Retry Experiment"
    assert experiment.status == "pending"
    assert len(experiment.scenarios) == 1


def test_experiment_generates_unique_ids():
    experiment_a = Experiment(
        name="Experiment A",
        scenarios=[make_scenario()]
    )

    experiment_b = Experiment(
        name="Experiment B",
        scenarios=[make_scenario()]
    )

    assert experiment_a.experiment_id != experiment_b.experiment_id


def test_experiment_has_creation_timestamp():
    experiment = Experiment(
        name="Timestamp Experiment",
        scenarios=[make_scenario()]
    )

    assert experiment.created_at is not None
    assert experiment.created_at.tzinfo is not None


def test_experiment_supports_multiple_scenarios():
    experiment = Experiment(
        name="Multiple Scenario Experiment",
        scenarios=[
            make_scenario("Timeout scenario"),
            FailureScenario(
                name="Rate limit scenario",
                failure_sequence=["rate_limit", "none"]
            )
        ]
    )

    assert len(experiment.scenarios) == 2


# --------------------------------------------------
# EXPERIMENT VALIDATION TESTS
# --------------------------------------------------

def test_experiment_rejects_empty_name():
    with pytest.raises(ValueError, match="Experiment name"):
        Experiment(
            name="   ",
            scenarios=[make_scenario()]
        )


def test_experiment_rejects_empty_scenarios():
    with pytest.raises(ValueError, match="at least one scenario"):
        Experiment(
            name="Invalid Experiment",
            scenarios=[]
        )


def test_experiment_rejects_invalid_status():
    with pytest.raises(ValueError, match="Invalid experiment status"):
        Experiment(
            name="Invalid Status Experiment",
            scenarios=[make_scenario()],
            status="unknown"
        )


def test_experiment_rejects_empty_id():
    with pytest.raises(ValueError, match="Experiment ID"):
        Experiment(
            name="Invalid ID Experiment",
            scenarios=[make_scenario()],
            experiment_id=""
        )


# --------------------------------------------------
# EXPERIMENT LIFECYCLE TESTS
# --------------------------------------------------

def test_experiment_can_start():
    experiment = Experiment(
        name="Start Experiment",
        scenarios=[make_scenario()]
    )

    experiment.start()

    assert experiment.status == "running"


def test_experiment_can_complete():
    experiment = Experiment(
        name="Complete Experiment",
        scenarios=[make_scenario()]
    )

    experiment.start()
    experiment.complete()

    assert experiment.status == "completed"


def test_experiment_can_fail():
    experiment = Experiment(
        name="Failed Experiment",
        scenarios=[make_scenario()]
    )

    experiment.start()
    experiment.fail()

    assert experiment.status == "failed"


def test_completed_experiment_cannot_start_again():
    experiment = Experiment(
        name="Completed Experiment",
        scenarios=[make_scenario()]
    )

    experiment.start()
    experiment.complete()

    with pytest.raises(ValueError):
        experiment.start()


def test_pending_experiment_cannot_complete():
    experiment = Experiment(
        name="Pending Experiment",
        scenarios=[make_scenario()]
    )

    with pytest.raises(ValueError):
        experiment.complete()


def test_pending_experiment_cannot_fail():
    experiment = Experiment(
        name="Pending Experiment",
        scenarios=[make_scenario()]
    )

    with pytest.raises(ValueError):
        experiment.fail()
