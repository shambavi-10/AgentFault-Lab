
from agentfault.faults import simulated_tool
from agentfault.models import ToolResult


class StochasticScenarioRunner:
    """Execute a predefined stochastic failure sequence."""

    def __init__(self, outcomes: list[str]):
        if not outcomes:
            raise ValueError("Outcome sequence cannot be empty")

        allowed_outcomes = {
            "none",
            "timeout",
            "rate_limit",
            "service_unavailable",
            "permission_denied",
            "malformed"
        }

        for outcome in outcomes:
            if outcome not in allowed_outcomes:
                raise ValueError(
                    f"Unsupported failure outcome: {outcome}"
                )

        self.outcomes = outcomes
        self.current_attempt = 0

    def run(self) -> ToolResult:
        """Return the next outcome in the sequence."""

        if self.current_attempt >= len(self.outcomes):
            raise RuntimeError(
                "Stochastic outcome sequence exhausted"
            )

        outcome = self.outcomes[self.current_attempt]
        self.current_attempt += 1

        return simulated_tool(outcome)
