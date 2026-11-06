
from pydantic import BaseModel


class ExecutionOverviewResponse(BaseModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    total_scenarios: int
    average_success_rate: float
    average_execution_time_ms: float
    total_retries: int


class ExecutionSuccessTrendResponse(BaseModel):
    run_id: str
    created_at: str
    success_rate: float
    passed_scenarios: int
    failed_scenarios: int


class ExecutionLatencyTrendResponse(BaseModel):
    run_id: str
    created_at: str
    total_execution_time_ms: float
    average_scenario_time_ms: float
    slowest_scenario_time_ms: float
    slowest_scenario_name: str | None


class ExecutionRetryTrendResponse(BaseModel):
    run_id: str
    created_at: str
    total_retries: int
    average_retries_per_scenario: float
    max_retries: int
    max_retry_scenario_name: str | None


class ExecutionFallbackTrendResponse(BaseModel):
    run_id: str
    created_at: str
    total_fallbacks: int
    average_fallbacks_per_scenario: float
    max_fallbacks: int
    max_fallback_scenario_name: str | None
    fallback_used: bool


class ExecutionCircuitBreakerTrendResponse(BaseModel):
    run_id: str
    created_at: str
    total_scenarios: int
    circuit_breaker_enabled_scenarios: int
    circuit_breaker_enabled_percentage: float


class ExecutionReliabilitySummaryResponse(BaseModel):
    total_runs: int
    total_scenarios: int
    reliability_score: float
    risk_level: str
    success_rate: float
    average_latency_ms: float
    average_retries: float
    fallback_usage_rate: float
    circuit_breaker_enabled_scenarios: int
    circuit_breaker_usage_rate: float
    metric_scores: dict[str, float]
    issues: list[str]
    recommendations: list[str]
