
from fastapi import FastAPI, HTTPException

from api.dependencies import get_dashboard_service
from api.routes.experiments import router as experiment_router

from agentfault.dashboard_service import DashboardServiceError
from api.routes.recommendations import router as recommendation_router

app = FastAPI(
    title="AgentFault Lab API",
    description="API for testing and analyzing AI agent reliability.",
    version="1.0.0",
)


app.include_router(experiment_router)

app.include_router(recommendation_router)
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


@app.get("/api/v1/dashboard")
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
