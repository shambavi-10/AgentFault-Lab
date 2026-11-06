
from fastapi import APIRouter, Depends

from api.execution_analytics_dependencies import (
    get_execution_analytics_service,
    get_execution_reliability_service,
)

from api.schemas.execution_analytics import (
    ExecutionOverviewResponse,
    ExecutionSuccessTrendResponse,
    ExecutionLatencyTrendResponse,
    ExecutionRetryTrendResponse,
    ExecutionFallbackTrendResponse,
    ExecutionCircuitBreakerTrendResponse,
    ExecutionReliabilitySummaryResponse,
)

from agentfault.services.execution_analytics_service import (
    ExecutionAnalyticsService,
)

from agentfault.services.execution_reliability_service import (
    ExecutionReliabilityService,
)


router = APIRouter(
    prefix="/api/v1/execution-analytics",
    tags=["Execution Analytics"],
)


@router.get(
    "/overview",
    response_model=ExecutionOverviewResponse,
)
def get_execution_overview(
    service: ExecutionAnalyticsService = Depends(
        get_execution_analytics_service
    ),
):
    """Retrieve aggregate execution metrics."""

    return service.get_execution_overview()


@router.get(
    "/trends/success",
    response_model=list[ExecutionSuccessTrendResponse],
)
def get_success_rate_trend(
    service: ExecutionAnalyticsService = Depends(
        get_execution_analytics_service
    ),
):
    """Retrieve execution success-rate trends."""

    return service.get_success_rate_trend()


@router.get(
    "/trends/latency",
    response_model=list[ExecutionLatencyTrendResponse],
)
def get_latency_trend(
    service: ExecutionAnalyticsService = Depends(
        get_execution_analytics_service
    ),
):
    """Retrieve execution latency trends."""

    return service.get_latency_trend()


@router.get(
    "/trends/retries",
    response_model=list[ExecutionRetryTrendResponse],
)
def get_retry_trend(
    service: ExecutionAnalyticsService = Depends(
        get_execution_analytics_service
    ),
):
    """Retrieve execution retry trends."""

    return service.get_retry_trend()


@router.get(
    "/trends/fallbacks",
    response_model=list[ExecutionFallbackTrendResponse],
)
def get_fallback_trend(
    service: ExecutionAnalyticsService = Depends(
        get_execution_analytics_service
    ),
):
    """Retrieve execution fallback trends."""

    return service.get_fallback_trend()


@router.get(
    "/trends/circuit-breaker",
    response_model=list[ExecutionCircuitBreakerTrendResponse],
)
def get_circuit_breaker_trend(
    service: ExecutionAnalyticsService = Depends(
        get_execution_analytics_service
    ),
):
    """Retrieve circuit-breaker usage trends."""

    return service.get_circuit_breaker_trend()


@router.get(
    "/reliability",
    response_model=ExecutionReliabilitySummaryResponse,
)
def get_execution_reliability_summary(
    service: ExecutionReliabilityService = Depends(
        get_execution_reliability_service
    ),
):
    """Retrieve execution reliability score and recommendations."""

    return service.generate_reliability_summary()
