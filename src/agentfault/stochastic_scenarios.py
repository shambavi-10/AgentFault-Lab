
import random

from agentfault.stochastic_faults import StochasticFaultSimulator


def generate_stochastic_sequences(
    experiments: int,
    tool_calls_per_experiment: int,
    timeout_probability: float = 0.1,
    rate_limit_probability: float = 0.1,
    seed: int | None = None
) -> list[list[str]]:

    if experiments < 1:
        raise ValueError("Experiments must be at least 1")

    if tool_calls_per_experiment < 1:
        raise ValueError(
            "Tool calls per experiment must be at least 1"
        )

    rng = random.Random(seed)

    sequences = []

    for experiment in range(experiments):

        experiment_seed = rng.randint(0, 2**32 - 1)

        simulator = StochasticFaultSimulator(
            timeout_probability=timeout_probability,
            rate_limit_probability=rate_limit_probability,
            seed=experiment_seed
        )

        outcomes = []

        for call in range(tool_calls_per_experiment):

            result = simulator.simulate()

            if result.status == "success":
                outcomes.append("none")
            else:
                outcomes.append(result.error_type)

        sequences.append(outcomes)

    return sequences
