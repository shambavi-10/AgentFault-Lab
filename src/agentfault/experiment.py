
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from typing import Literal

from agentfault.scenarios import FailureScenario
from agentfault.reliability_config import ReliabilityConfig


ExperimentStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed"
]


@dataclass
class Experiment:
    """Represents an experiment in AgentFault Lab."""

    name: str
    scenarios: list[FailureScenario]
    description: str = ""
    reliability_config: ReliabilityConfig = field(
        default_factory=ReliabilityConfig
    )

    experiment_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    status: ExperimentStatus = "pending"

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Experiment name cannot be empty")

        if not self.scenarios:
            raise ValueError(
                "An experiment must contain at least one scenario"
            )

        if not isinstance(self.experiment_id, str):
            raise ValueError("Experiment ID must be a string")

        if not self.experiment_id.strip():
            raise ValueError("Experiment ID cannot be empty")

        if self.status not in {
            "pending",
            "running",
            "completed",
            "failed"
        }:
            raise ValueError("Invalid experiment status")

    def start(self):
        """Start a pending experiment."""
        if self.status != "pending":
            raise ValueError(
                "Only pending experiments can be started"
            )

        self.status = "running"

    def complete(self):
        """Mark a running experiment as completed."""
        if self.status != "running":
            raise ValueError(
                "Only running experiments can be completed"
            )

        self.status = "completed"

    def fail(self):
        """Mark a running experiment as failed."""
        if self.status != "running":
            raise ValueError(
                "Only running experiments can be failed"
            )

        self.status = "failed"
