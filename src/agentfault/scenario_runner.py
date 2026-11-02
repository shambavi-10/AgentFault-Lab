from agentfault.faults import simulated_tool
from agentfault.models import ToolResult
from agentfault.scenarios import FailureScenario


class ScenarioRunner:
    """Executes a predefined sequence of simulated tool outcomes."""

    def __init__(self, scenario: FailureScenario):
        self.scenario = scenario
        self.current_attempt = 0

    def run(self) -> ToolResult:
        """Return the next outcome in the scenario sequence."""

        if self.current_attempt >= len(self.scenario.failure_sequence):
            raise RuntimeError("Scenario sequence exhausted")

        outcome = self.scenario.failure_sequence[
            self.current_attempt
        ]

        self.current_attempt += 1

        return simulated_tool(outcome)