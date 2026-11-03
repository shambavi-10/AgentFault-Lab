
import random

from agentfault.faults import simulated_tool
from agentfault.models import ToolResult


class StochasticFaultSimulator:
    """Generate controlled random tool failures."""

    def __init__(
        self,
        timeout_probability: float = 0.1,
        rate_limit_probability: float = 0.1,
        seed: int | None = None
    ):
        if not 0 <= timeout_probability <= 1:
            raise ValueError(
                "Timeout probability must be between 0 and 1"
            )

        if not 0 <= rate_limit_probability <= 1:
            raise ValueError(
                "Rate-limit probability must be between 0 and 1"
            )

        if timeout_probability + rate_limit_probability > 1:
            raise ValueError(
                "Total failure probability cannot exceed 1"
            )

        self.timeout_probability = timeout_probability
        self.rate_limit_probability = rate_limit_probability

        # Use a separate random generator for reproducibility.
        self.rng = random.Random(seed)

    def simulate(self) -> ToolResult:
        """Generate one random tool outcome."""

        random_value = self.rng.random()

        if random_value < self.timeout_probability:
            return simulated_tool("timeout")

        if random_value < (
            self.timeout_probability + self.rate_limit_probability
        ):
            return simulated_tool("rate_limit")

        return simulated_tool("none")
