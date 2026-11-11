
import pytest

from agentfault.stochastic_scenarios import (
    generate_stochastic_sequences,
)


def test_generate_stochastic_sequences_rejects_zero_experiments():
    with pytest.raises(
        ValueError,
        match="Experiments must be at least 1",
    ):
        generate_stochastic_sequences(
            experiments=0,
            tool_calls_per_experiment=5,
        )


def test_generate_stochastic_sequences_rejects_zero_tool_calls():
    with pytest.raises(
        ValueError,
        match="Tool calls per experiment must be at least 1",
    ):
        generate_stochastic_sequences(
            experiments=2,
            tool_calls_per_experiment=0,
        )


def test_generate_stochastic_sequences_is_reproducible():
    first = generate_stochastic_sequences(
        experiments=3,
        tool_calls_per_experiment=5,
        seed=42,
    )

    second = generate_stochastic_sequences(
        experiments=3,
        tool_calls_per_experiment=5,
        seed=42,
    )

    assert first == second
    assert len(first) == 3
    assert all(len(sequence) == 5 for sequence in first)


def test_generate_stochastic_sequences_returns_valid_outcomes():
    sequences = generate_stochastic_sequences(
        experiments=3,
        tool_calls_per_experiment=10,
        seed=42,
    )

    allowed_outcomes = {
        "none",
        "timeout",
        "rate_limit",
        "service_unavailable",
        "permission_denied",
        "malformed",
    }

    assert len(sequences) == 3

    for sequence in sequences:
        assert len(sequence) == 10
        assert all(
            outcome in allowed_outcomes
            for outcome in sequence
        )
