from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import (
    get_recommendation_engine,
    get_recommendation_manager,
)
from api.schemas.experiment import (
    ReliabilityRecommendationResponse,
    RecommendationGenerationResponse,
    RecommendationSummaryResponse,
)

from agentfault.recommendation_engine import (
    RecommendationEngine,
    RecommendationEngineError,
)
from agentfault.recommendation_manager import (
    RecommendationManager,
    RecommendationManagerError,
)


router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["Recommendations"],
)


@router.post(
    "/generate/{experiment_id}",
    response_model=RecommendationGenerationResponse,
)
def generate_recommendations(
    experiment_id: str,
    engine: RecommendationEngine = Depends(get_recommendation_engine),
    manager: RecommendationManager = Depends(get_recommendation_manager),
):
    """Generate and persist recommendations for an experiment."""

    try:
        recommendations = engine.generate_recommendations(experiment_id)

        saved = manager.add_recommendations(recommendations)

        return RecommendationGenerationResponse(
            experiment_id=experiment_id,
            total_generated=len(saved),
            recommendations=saved,
        )

    except RecommendationEngineError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        raise HTTPException(status_code=500, detail=str(exc)) from exc

    except RecommendationManagerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "",
    response_model=list[ReliabilityRecommendationResponse],
)
def list_recommendations(
    priority: str | None = Query(default=None),
    category: str | None = Query(default=None),
    recommendation_status: str | None = Query(default=None, alias="status"),
    manager: RecommendationManager = Depends(get_recommendation_manager),
):
    """List recommendations with optional filters."""

    try:
        return manager.filter_recommendations(
            priority=priority,
            category=category,
            status=recommendation_status,
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except RecommendationManagerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/summary",
    response_model=RecommendationSummaryResponse,
)
def get_recommendation_summary(
    manager: RecommendationManager = Depends(get_recommendation_manager),
):
    """Retrieve recommendation management statistics."""

    try:
        return manager.get_summary()

    except RecommendationManagerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/{recommendation_id}",
    response_model=ReliabilityRecommendationResponse,
)
def get_recommendation(
    recommendation_id: str,
    manager: RecommendationManager = Depends(get_recommendation_manager),
):
    """Retrieve one recommendation by its ID."""

    try:
        recommendation = manager.get_recommendation(recommendation_id)

        if recommendation is None:
            raise HTTPException(
                status_code=404,
                detail="Recommendation not found",
            )

        return recommendation

    except RecommendationManagerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc