from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import (
    get_historical_analytics,
    get_historical_insights,
)

from api.schemas.experiment import (
    ReliabilityInsightsResponse,
    SuccessRateTrendResponse,
    LatencyTrendResponse,
    RetryTrendResponse,
    FallbackTrendResponse,
    HistoricalSummaryResponse,
    HistoricalComparisonResponse,
)

from agentfault.historical_analytics import (
    HistoricalAnalytics,
    HistoricalAnalyticsError,
)

from agentfault.historical_insights import (
    HistoricalInsights,
    HistoricalInsightsError,
)


router = APIRouter(
    prefix="/api/v1/insights",
    tags=["Historical Insights"],
)


# --------------------------------------------------
# 1. All experiment insights
# --------------------------------------------------

@router.get(
    "",
    response_model=list[ReliabilityInsightsResponse],
)
def get_all_experiment_insights(
    insights: HistoricalInsights = Depends(get_historical_insights),
):
    """Retrieve reliability insights for all saved experiments."""

    try:
        results = insights.analyze_all_experiments()

        return [
            ReliabilityInsightsResponse(**result.__dict__)
            for result in results
        ]

    except HistoricalInsightsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --------------------------------------------------
# 2. Historical trends
# --------------------------------------------------

@router.get(
    "/trends/success",
    response_model=list[SuccessRateTrendResponse],
)
def get_success_rate_trend(
    analytics: HistoricalAnalytics = Depends(get_historical_analytics),
):
    """Retrieve historical success-rate trends."""

    try:
        return analytics.get_success_rate_trend()

    except HistoricalAnalyticsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/trends/latency",
    response_model=list[LatencyTrendResponse],
)
def get_latency_trend(
    analytics: HistoricalAnalytics = Depends(get_historical_analytics),
):
    """Retrieve historical latency trends."""

    try:
        return analytics.get_latency_trend()

    except HistoricalAnalyticsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/trends/retries",
    response_model=list[RetryTrendResponse],
)
def get_retry_trend(
    analytics: HistoricalAnalytics = Depends(get_historical_analytics),
):
    """Retrieve historical retry trends."""

    try:
        return analytics.get_retry_trend()

    except HistoricalAnalyticsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/trends/fallbacks",
    response_model=list[FallbackTrendResponse],
)
def get_fallback_trend(
    analytics: HistoricalAnalytics = Depends(get_historical_analytics),
):
    """Retrieve historical fallback trends."""

    try:
        return analytics.get_fallback_trend()

    except HistoricalAnalyticsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --------------------------------------------------
# 3. Best and worst experiments
# --------------------------------------------------

@router.get("/best")
def get_best_experiment(
    analytics: HistoricalAnalytics = Depends(get_historical_analytics),
):
    """Retrieve the experiment with the highest success rate."""

    try:
        result = analytics.get_best_experiment()

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="No historical experiments found",
            )

        return result

    except HistoricalAnalyticsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/worst")
def get_worst_experiment(
    analytics: HistoricalAnalytics = Depends(get_historical_analytics),
):
    """Retrieve the experiment with the lowest success rate."""

    try:
        result = analytics.get_worst_experiment()

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="No historical experiments found",
            )

        return result

    except HistoricalAnalyticsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --------------------------------------------------
# 4. Historical summary
# --------------------------------------------------

@router.get(
    "/summary",
    response_model=HistoricalSummaryResponse,
)
def get_historical_summary(
    analytics: HistoricalAnalytics = Depends(get_historical_analytics),
):
    """Retrieve overall historical reliability statistics."""

    try:
        return analytics.get_historical_summary()

    except HistoricalAnalyticsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --------------------------------------------------
# 5. Historical comparison
# --------------------------------------------------

@router.get(
    "/compare",
    response_model=HistoricalComparisonResponse,
)
def compare_historical_experiments(
    first_experiment_id: str = Query(min_length=1),
    second_experiment_id: str = Query(min_length=1),
    analytics: HistoricalAnalytics = Depends(get_historical_analytics),
):
    """Compare reliability metrics between two experiments."""

    try:
        return analytics.compare_experiments(
            first_experiment_id,
            second_experiment_id,
        )

    except HistoricalAnalyticsError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --------------------------------------------------
# 6. Individual experiment insights
# --------------------------------------------------

@router.get(
    "/{experiment_id}",
    response_model=ReliabilityInsightsResponse,
)
def get_experiment_insights(
    experiment_id: str,
    insights: HistoricalInsights = Depends(get_historical_insights),
):
    """Retrieve reliability insights for one experiment."""

    try:
        result = insights.analyze_experiment(experiment_id)
        return ReliabilityInsightsResponse(**result.__dict__)

    except HistoricalInsightsError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        raise HTTPException(status_code=500, detail=str(exc)) from exc