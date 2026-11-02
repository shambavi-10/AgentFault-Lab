from dataclasses import dataclass
from typing import Literal


@dataclass
class AgentConfig:
    """Configuration for an agent's retry behavior."""

    name: str
    max_attempts: int
    retry_strategy: Literal["none", "fixed", "exponential"]
    base_delay: float = 0.0
    max_delay: float = 30.0
    jitter: bool = False

    def __post_init__(self):
        if not self.name:
            raise ValueError("Agent name cannot be empty")

        if self.max_attempts < 1:
            raise ValueError("Maximum attempts must be at least 1")

        if self.retry_strategy not in {
            "none",
            "fixed",
            "exponential"
        }:
            raise ValueError("Unsupported retry strategy")

        if self.retry_strategy == "none" and self.max_attempts != 1:
            raise ValueError(
                "Agent without retries must have exactly one attempt"
            )

        if self.base_delay < 0 or self.max_delay < 0:
            raise ValueError("Retry delays cannot be negative")