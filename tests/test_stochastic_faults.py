
import pytest

from agentfault.stochastic_faults import StochasticFaultSimulator


def test_same_seed_produces_same_results():

    simulator_a = StochasticFaultSimulator(
        timeout_probability=0.3,
        rate_limit_probability=0.2,
        seed=42
    )

    simulator_b = StochasticFaultSimulator(
        timeout_probability=0.3,
        rate_limit_probability=0.2,
        seed=42
    )

    results_a = [
        simulator_a.simulate() for _ in range(20)
    ]

    results_b = [
        simulator_b.simulate() for _ in range(20)
    ]

    outcomes_a = [
        (result.status, result.error_type)
        for result in results_a
    ]

    outcomes_b = [
        (result.status, result.error_type)
        for result in results_b
    ]

    assert outcomes_a == outcomes_b


def test_different_seeds_can_produce_different_results():

    simulator_a = StochasticFaultSimulator(seed=42)
    simulator_b = StochasticFaultSimulator(seed=99)

    results_a = [
        simulator_a.simulate().error_type for _ in range(50)
    ]

    results_b = [
        simulator_b.simulate().error_type for _ in range(50)
    ]

    assert results_a != results_b


def test_invalid_timeout_probability():

    with pytest.raises(ValueError):
        StochasticFaultSimulator(
            timeout_probability=1.5
        )


def test_invalid_rate_limit_probability():

    with pytest.raises(ValueError):
        StochasticFaultSimulator(
            rate_limit_probability=-0.2
        )


def test_combined_failure_probability_cannot_exceed_one():

    with pytest.raises(ValueError):
        StochasticFaultSimulator(
            timeout_probability=0.7,
            rate_limit_probability=0.5
        )


def test_zero_failure_probability_always_succeeds():

    simulator = StochasticFaultSimulator(
        timeout_probability=0,
        rate_limit_probability=0,
        seed=42
    )

    results = [
        simulator.simulate() for _ in range(100)
    ]

    assert all(result.status == "success" for result in results)


def test_full_timeout_probability_always_times_out():

    simulator = StochasticFaultSimulator(
        timeout_probability=1,
        rate_limit_probability=0,
        seed=42
    )

    results = [
        simulator.simulate() for _ in range(100)
    ]

    assert all(
        result.status == "failure"
        and result.error_type == "timeout"
        for result in results
    )
