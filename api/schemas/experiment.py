
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FailureOutcome = Literal[
    "none",
    "timeout",
    "rate_limit",
    "service_unavailable",
    "permission_denied",
    "malformed",
]


class FailureScenarioRequest(BaseModel):
    """Request schema for an experiment failure scenario."""

    name: str = Field(min_length=1)
    failure_sequence: list[FailureOutcome] = Field(min_length=1)
    expected_status: Literal["success", "failure"] = "success"


class ReliabilityConfigRequest(BaseModel):
    """Request schema for reliability configuration."""

    max_attempts: int = Field(default=3, ge=1)
    retry_strategy: Literal["none", "fixed", "exponential"] = "exponential"

    base_delay: float = Field(default=1.0, ge=0)
    max_delay: float = Field(default=30.0, ge=0)
    jitter: bool = True

    enable_circuit_breaker: bool = False
    failure_threshold: int = Field(default=3, ge=1)
    recovery_timeout: float = Field(default=10.0, ge=0)

    enable_fallback: bool = True


class ExperimentCreateRequest(BaseModel):
    """Request schema for creating an experiment."""

    name: str = Field(min_length=1)
    description: str = ""

    scenarios: list[FailureScenarioRequest] = Field(min_length=1)

    reliability_config: ReliabilityConfigRequest = Field(
        default_factory=ReliabilityConfigRequest
    )


class ExperimentResponse(BaseModel):
    """Response schema for experiment details."""

    model_config = ConfigDict(from_attributes=True)

    experiment_id: str
    name: str
    description: str
    status: str
    created_at: datetime
    scenarios: list[FailureScenarioRequest]
    reliability_config: ReliabilityConfigRequest
