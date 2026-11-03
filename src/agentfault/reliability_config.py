
from dataclasses import dataclass
from typing import Literal


@dataclass
class ReliabilityConfig:
    """Configuration for unified reliability execution."""

    # Retry settings
    max_attempts: int = 3
    retry_strategy: Literal[
        "none", "fixed", "exponential"
    ] = "exponential"

    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True

    # Circuit breaker settings
    enable_circuit_breaker: bool = False
    failure_threshold: int = 3
    recovery_timeout: float = 10.0

    # Fallback settings
    enable_fallback: bool = True

    def __post_init__(self):
        if self.max_attempts < 1:
            raise ValueError(
                "Maximum attempts must be at least 1"
            )

        if self.retry_strategy not in {
            "none", "fixed", "exponential"
        }:
            raise ValueError(
                "Unsupported retry strategy"
            )

        if self.retry_strategy == "none":
            self.max_attempts = 1

        if self.base_delay < 0 or self.max_delay < 0:
            raise ValueError(
                "Retry delays cannot be negative"
            )

        if self.failure_threshold < 1:
            raise ValueError(
                "Failure threshold must be at least 1"
            )

        if self.recovery_timeout < 0:
            raise ValueError(
                "Recovery timeout cannot be negative"
            )
