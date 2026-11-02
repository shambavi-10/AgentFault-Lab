from dataclasses import dataclass


@dataclass
class FailureScenario:
    """Defines a repeatable tool failure scenario."""

    name: str
    failure_sequence: list[str]
    expected_status: str = "success"

    def __post_init__(self):
        if not self.name:
            raise ValueError("Scenario name cannot be empty")

        if not self.failure_sequence:
            raise ValueError("Failure sequence cannot be empty")

        allowed_outcomes = {
            "none",
            "timeout",
            "rate_limit",
            "service_unavailable",
            "permission_denied",
            "malformed"
        }

        for outcome in self.failure_sequence:
            if outcome not in allowed_outcomes:
                raise ValueError(
                    f"Unsupported failure outcome: {outcome}"
                )

        if self.expected_status not in {"success", "failure"}:
            raise ValueError("Invalid expected status")