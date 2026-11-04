
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


class TraceEventResponse(BaseModel):
    """Response schema for an individual trace event."""

    event_type: str
    execution_id: str
    attempt: int
    status: str | None = None
    error_type: str | None = None
    message: str | None = None
    duration_ms: float | None = None
    timestamp: str


class ExecutionTraceResponse(BaseModel):
    """Response schema for an execution trace."""

    execution_id: str
    events: list[TraceEventResponse]


class ScenarioExecutionResultResponse(BaseModel):
    """Response schema for one scenario execution."""

    scenario_name: str
    expected_status: str
    result: dict
    trace: ExecutionTraceResponse
    execution_time_ms: float
    retry_count: int
    fallback_count: int
    fallback_used: bool
    circuit_breaker_enabled: bool
    valid_business_result: bool
    passed: bool


class ExperimentExecutionResponse(BaseModel):
    """Response schema for a complete experiment execution."""

    experiment_id: str
    experiment_name: str
    status: str
    scenario_results: list[ScenarioExecutionResultResponse]
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    success_rate: float
    total_execution_time_ms: float
    total_retries: int
