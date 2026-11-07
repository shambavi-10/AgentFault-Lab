
import pytest

from agentfault.stochastic_scenario_runner import (
    StochasticScenarioRunner,
)


@pytest.mark.parametrize(
    "outcome",
    [
        "none",
        "timeout",
        "rate_limit",
        "service_unavailable",
        "permission_denied",
        "malformed",
    ],
)
def test_runner_accepts_supported_outcomes(outcome):
    runner = StochasticScenarioRunner([outcome])

    assert runner.outcomes == [outcome]
    assert runner.current_attempt == 0


def test_runner_rejects_empty_outcome_sequence():
    with pytest.raises(
        ValueError,
        match="Outcome sequence cannot be empty",
    ):
        StochasticScenarioRunner([])


def test_runner_rejects_unsupported_outcome():
    with pytest.raises(
        ValueError,
        match="Unsupported failure outcome",
    ):
        StochasticScenarioRunner(["invalid_outcome"])


def test_runner_raises_when_sequence_is_exhausted():
    runner = StochasticScenarioRunner(["none"])

    runner.run()

    with pytest.raises(
        RuntimeError,
        match="Stochastic outcome sequence exhausted",
    ):
        runner.run()
