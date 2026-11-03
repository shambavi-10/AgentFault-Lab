
from agentfault.models import ToolResult
from agentfault.stochastic_faults import StochasticFaultSimulator


class StochasticToolRunner:
    """Runs a tool using controlled stochastic failures."""

    def __init__(
        self,
        timeout_probability: float = 0.1,
        rate_limit_probability: float = 0.1,
        seed: int | None = None
    ):
        self.simulator = StochasticFaultSimulator(
            timeout_probability=timeout_probability,
            rate_limit_probability=rate_limit_probability,
            seed=seed
        )

    def run(self) -> ToolResult:
        """Generate one stochastic tool outcome."""

        return self.simulator.simulate()
