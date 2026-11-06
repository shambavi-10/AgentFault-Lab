
from fastapi import FastAPI, HTTPException

from api.dependencies import get_dashboard_service
from api.routes.experiments import router as experiment_router

from agentfault.dashboard_service import DashboardServiceError
from api.schemas.dashboard import DashboardResponse
from api.routes.recommendations import router as recommendation_router
from api.routes.insights import router as insights_router
from api.routes.execution_analytics import (
    router as execution_analytics_router,
)

app = FastAPI(
    title="AgentFault Lab API",
    description="""
    # AgentFault Lab API

    Enterprise AI Agent Reliability Testing and Chaos Engineering Platform.

    This API allows developers and AI engineering teams to:

    - Register and manage AI reliability experiments.
    - Execute experiments and simulate failures.
    - Evaluate retry, fallback and circuit breaker strategies.
    - Generate benchmark reports and analytics.
    - Analyze historical reliability performance.
    - Generate and manage reliability recommendations.
    - Monitor overall system reliability through dashboards.

    ## API Version

    Version: 1.0.0

    Base path: `/api/v1`
    """,
    version="1.0.0",
        openapi_tags=[
        {
            "name": "Experiments",
            "description": (
                "Create, execute, compare and manage AI agent "
                "reliability experiments, benchmarks and reports."
            ),
        },
        {
            "name": "Recommendations",
            "description": (
                "Generate, retrieve, filter and manage "
                "AI agent reliability recommendations."
            ),
        },
        {
            "name": "Historical Insights",
            "description": (
                "Analyze historical experiment performance, "
                "reliability trends and comparisons."
            ),
        },
        {
            "name": "Dashboard",
            "description": (
                "View aggregated experiment activity, reliability metrics, "
                "recommendations and performance trends."
            ),
        },
        {
            "name": "Execution Analytics",
            "description": (
                "Analyze execution history, success rates, latency, "
                "retries, fallback usage and reliability scores."
            ),
        },
    ],
)
   
app.include_router(insights_router)
app.include_router(experiment_router)
app.include_router(recommendation_router)
app.include_router(execution_analytics_router)

@app.get("/")
def root():
    """Return basic API information."""

    return {
        "message": "Welcome to AgentFault Lab API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    """Check whether the API is running."""

    return {
        "status": "healthy",
    }


@app.get(
    "/api/v1/dashboard",
    response_model=DashboardResponse,
    tags=["Dashboard"],
    summary="Get Dashboard Overview",
    description=(
        "Retrieve aggregated AgentFault Lab dashboard data, "
        "including experiment statistics, reliability metrics, "
        "recommendations and performance trends."
    ),
)
def get_dashboard():
    """Return aggregated AgentFault Lab dashboard data."""

    try:
        dashboard_service = get_dashboard_service()

        return dashboard_service.get_dashboard_data()

    except DashboardServiceError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc