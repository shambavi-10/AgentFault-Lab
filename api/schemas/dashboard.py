from pydantic import BaseModel

from api.schemas.experiment import (
    BenchmarkReportResponse,
    SuccessRateTrendResponse,
    LatencyTrendResponse,
    RetryTrendResponse,
    FallbackTrendResponse,
    RecommendationSummaryResponse,
)


class ExperimentOverviewResponse(BaseModel):
    total_experiments: int
    completed_experiments: int
    failed_experiments: int
    average_success_rate: float
    average_latency_ms: float
    total_retries: int
    total_fallbacks: int


class ReliabilityOverviewResponse(BaseModel):
    average_reliability_score: float
    low_risk_experiments: int
    medium_risk_experiments: int
    high_risk_experiments: int
    risk_distribution: dict[str, int]


class PerformanceTrendsResponse(BaseModel):
    success_rate: list[SuccessRateTrendResponse]
    latency: list[LatencyTrendResponse]
    retries: list[RetryTrendResponse]
    fallbacks: list[FallbackTrendResponse]


class ExperimentHighlightsResponse(BaseModel):
    best_experiment: BenchmarkReportResponse | None
    worst_experiment: BenchmarkReportResponse | None


class DashboardResponse(BaseModel):
    experiment_overview: ExperimentOverviewResponse
    reliability_overview: ReliabilityOverviewResponse
    recommendation_overview: RecommendationSummaryResponse
    performance_trends: PerformanceTrendsResponse
    experiment_highlights: ExperimentHighlightsResponse