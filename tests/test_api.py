
import pytest

from fastapi.testclient import TestClient

import api.main as main

from api.experiment_dependencies import get_experiment_manager
from agentfault.experiment_manager import ExperimentManager
from agentfault.dashboard_service import DashboardServiceError
from api.execution_dependencies import get_execution_results_store
from api.dependencies import (
    get_recommendation_manager,
    get_report_manager,
    get_historical_analytics,
    get_historical_insights,
    get_recommendation_engine,
)

from agentfault.recommendation_manager import RecommendationManager
from agentfault.report_storage import ReportStorage
from agentfault.report_manager import ReportManager
from agentfault.historical_analytics import HistoricalAnalytics
from agentfault.historical_insights import HistoricalInsights
from agentfault.recommendation_engine import RecommendationEngine

@pytest.fixture
def experiment_manager():
    return ExperimentManager()

@pytest.fixture
def client(experiment_manager, tmp_path):
    get_execution_results_store().clear()

    report_manager = ReportManager(
        ReportStorage(
            storage_dir=tmp_path / "reports"
        )
    )

    recommendation_manager = RecommendationManager(
        storage_path=tmp_path / "recommendations.json"
    )

    historical_analytics = HistoricalAnalytics(
        report_manager
    )

    historical_insights = HistoricalInsights(
        historical_analytics
    )

    recommendation_engine = RecommendationEngine(
        insights=historical_insights
    )

    main.app.dependency_overrides[get_experiment_manager] = (
        lambda: experiment_manager
    )

    main.app.dependency_overrides[get_report_manager] = (
        lambda: report_manager
    )

    main.app.dependency_overrides[get_recommendation_manager] = (
        lambda: recommendation_manager
    )

    main.app.dependency_overrides[get_historical_analytics] = (
        lambda: historical_analytics
    )

    main.app.dependency_overrides[get_historical_insights] = (
        lambda: historical_insights
    )

    main.app.dependency_overrides[get_recommendation_engine] = (
        lambda: recommendation_engine
    )

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()

def valid_experiment_payload():
    return {
        "name": "API Experiment Test",
        "description": "Testing experiment management API",
        "scenarios": [
            {
                "name": "Normal Execution",
                "failure_sequence": ["none"],
                "expected_status": "success",
            },
            {
                "name": "Timeout Recovery",
                "failure_sequence": ["timeout", "none"],
                "expected_status": "success",
            },
        ],
        "reliability_config": {
            "max_attempts": 3,
            "retry_strategy": "exponential",
            "base_delay": 1.0,
            "max_delay": 30.0,
            "jitter": True,
            "enable_circuit_breaker": False,
            "failure_threshold": 3,
            "recovery_timeout": 10.0,
            "enable_fallback": True,
        },
    }


# --------------------------------------------------
# Existing API tests
# --------------------------------------------------

def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to AgentFault Lab API",
        "status": "running",
    }


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
    }


def test_dashboard_endpoint(client, monkeypatch):
    expected_data = {
        "experiment_overview": {
            "total_experiments": 4,
        },
        "reliability_overview": {
            "average_reliability_score": 89.62,
        },
    }

    class FakeDashboardService:
        def get_dashboard_data(self):
            return expected_data

    monkeypatch.setattr(
        main,
        "get_dashboard_service",
        lambda: FakeDashboardService(),
    )

    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    assert response.json() == expected_data


def test_dashboard_error_handling(client, monkeypatch):
    class FakeDashboardService:
        def get_dashboard_data(self):
            raise DashboardServiceError(
                "Unable to generate dashboard data"
            )

    monkeypatch.setattr(
        main,
        "get_dashboard_service",
        lambda: FakeDashboardService(),
    )

    response = client.get("/api/v1/dashboard")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to generate dashboard data",
    }


# --------------------------------------------------
# Experiment creation tests
# --------------------------------------------------

def test_create_experiment(client):
    response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "API Experiment Test"
    assert data["status"] == "pending"
    assert len(data["scenarios"]) == 2
    assert data["experiment_id"]


def test_create_experiment_with_invalid_scenario(client):
    payload = valid_experiment_payload()

    payload["scenarios"][0]["failure_sequence"] = [
        "invalid_failure"
    ]

    response = client.post(
        "/api/v1/experiments",
        json=payload,
    )

    assert response.status_code == 422


def test_create_experiment_without_scenarios(client):
    payload = valid_experiment_payload()
    payload["scenarios"] = []

    response = client.post(
        "/api/v1/experiments",
        json=payload,
    )

    assert response.status_code == 422


# --------------------------------------------------
# Experiment listing tests
# --------------------------------------------------

def test_list_experiments(client):
    client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    response = client.get("/api/v1/experiments")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "API Experiment Test"


def test_list_experiments_when_empty(client):
    response = client.get("/api/v1/experiments")

    assert response.status_code == 200
    assert response.json() == []


# --------------------------------------------------
# Experiment retrieval tests
# --------------------------------------------------

def test_get_experiment_by_id(client):
    create_response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    experiment_id = create_response.json()["experiment_id"]

    response = client.get(
        f"/api/v1/experiments/{experiment_id}"
    )

    assert response.status_code == 200
    assert response.json()["experiment_id"] == experiment_id


def test_get_nonexistent_experiment(client):
    response = client.get(
        "/api/v1/experiments/nonexistent-id"
    )

    assert response.status_code == 404


# --------------------------------------------------
# Experiment deletion tests
# --------------------------------------------------

def test_delete_experiment(client):
    create_response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    experiment_id = create_response.json()["experiment_id"]

    response = client.delete(
        f"/api/v1/experiments/{experiment_id}"
    )

    assert response.status_code == 204

    get_response = client.get(
        f"/api/v1/experiments/{experiment_id}"
    )

    assert get_response.status_code == 404


def test_delete_nonexistent_experiment(client):
    response = client.delete(
        "/api/v1/experiments/nonexistent-id"
    )

    assert response.status_code == 404


def test_delete_running_experiment(
    client,
    experiment_manager,
):
    create_response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    experiment_id = create_response.json()["experiment_id"]

    experiment_manager.start_experiment(experiment_id)

    response = client.delete(
        f"/api/v1/experiments/{experiment_id}"
    )

    assert response.status_code == 409


# --------------------------------------------------
# Experiment execution tests
# --------------------------------------------------

def test_run_experiment_successfully(client):
    create_response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    experiment_id = create_response.json()["experiment_id"]

    response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["experiment_id"] == experiment_id
    assert data["experiment_name"] == "API Experiment Test"
    assert data["status"] == "completed"

    assert data["total_scenarios"] == 2
    assert data["passed_scenarios"] == 2
    assert data["failed_scenarios"] == 0

    assert data["success_rate"] == 1.0
    assert len(data["scenario_results"]) == 2

    first_result = data["scenario_results"][0]

    assert first_result["scenario_name"] == "Normal Execution"
    assert first_result["passed"] is True
    assert first_result["result"]["status"] == "success"
    assert first_result["trace"]["execution_id"]


def test_run_nonexistent_experiment(client):
    response = client.post(
        "/api/v1/experiments/nonexistent-id/run"
    )

    assert response.status_code == 404


def test_run_experiment_updates_experiment_status(client):
    create_response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    experiment_id = create_response.json()["experiment_id"]

    run_response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )

    assert run_response.status_code == 200

    get_response = client.get(
        f"/api/v1/experiments/{experiment_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "completed"

# --------------------------------------------------
# Experiment results retrieval tests
# --------------------------------------------------

def test_get_experiment_results_successfully(client):
    create_response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    experiment_id = create_response.json()["experiment_id"]

    run_response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )

    assert run_response.status_code == 200

    response = client.get(
        f"/api/v1/experiments/{experiment_id}/results"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["experiment_id"] == experiment_id
    assert data["experiment_name"] == "API Experiment Test"
    assert data["status"] == "completed"
    assert data["total_scenarios"] == 2
    assert data["passed_scenarios"] == 2
    assert data["success_rate"] == 1.0
    assert len(data["scenario_results"]) == 2


def test_get_results_before_experiment_execution(client):
    create_response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    experiment_id = create_response.json()["experiment_id"]

    response = client.get(
        f"/api/v1/experiments/{experiment_id}/results"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No execution results found for this experiment"
    )


def test_get_results_for_nonexistent_experiment(client):
    response = client.get(
        "/api/v1/experiments/nonexistent-id/results"
    )

    assert response.status_code == 404

# --------------------------------------------------
# Experiment execution history tests
# --------------------------------------------------

def test_get_experiment_history_successfully(client):
    create_response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    experiment_id = create_response.json()["experiment_id"]

    run_response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )

    assert run_response.status_code == 200

    response = client.get(
        f"/api/v1/experiments/{experiment_id}/history"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["experiment_id"] == experiment_id
    assert data[0]["status"] == "completed"
    assert data[0]["total_scenarios"] == 2


def test_get_empty_experiment_history(client):
    create_response = client.post(
        "/api/v1/experiments",
        json=valid_experiment_payload(),
    )

    experiment_id = create_response.json()["experiment_id"]

    response = client.get(
        f"/api/v1/experiments/{experiment_id}/history"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_history_for_nonexistent_experiment(client):
    response = client.get(
        "/api/v1/experiments/nonexistent-id/history"
    )

    assert response.status_code == 404

# --------------------------------------------------
# Experiment comparison API tests
# --------------------------------------------------

def test_compare_experiment_strategies_successfully(client):
    payload = {
        "scenarios": [
            {
                "name": "Timeout Recovery",
                "failure_sequence": ["timeout", "none"],
                "expected_status": "success",
            }
        ],
        "strategies": {
            "no_retry": {
                "max_attempts": 1,
                "retry_strategy": "none",
                "base_delay": 0.0,
                "max_delay": 0.0,
                "jitter": False,
                "enable_circuit_breaker": False,
                "failure_threshold": 3,
                "recovery_timeout": 10.0,
                "enable_fallback": False,
            },
            "retry_enabled": {
                "max_attempts": 3,
                "retry_strategy": "exponential",
                "base_delay": 0.0,
                "max_delay": 0.0,
                "jitter": False,
                "enable_circuit_breaker": False,
                "failure_threshold": 3,
                "recovery_timeout": 10.0,
                "enable_fallback": False,
            },
        },
    }

    response = client.post(
        "/api/v1/experiments/compare",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_strategies"] == 2
    assert data["best_strategy"] in [
        "no_retry",
        "retry_enabled",
    ]

    assert len(data["comparisons"]) == 2

    for comparison in data["comparisons"]:
        assert comparison["strategy_name"] in [
            "no_retry",
            "retry_enabled",
        ]
        assert comparison["experiment_execution"]["status"] == "completed"
        assert comparison["success_rate"] >= 0.0
        assert comparison["total_retries"] >= 0


def test_compare_experiments_without_scenarios(client):
    payload = {
        "scenarios": [],
        "strategies": {
            "baseline": {}
        },
    }

    response = client.post(
        "/api/v1/experiments/compare",
        json=payload,
    )

    assert response.status_code == 422


def test_compare_experiments_without_strategies(client):
    payload = {
        "scenarios": [
            {
                "name": "Normal Execution",
                "failure_sequence": ["none"],
                "expected_status": "success",
            }
        ],
        "strategies": {},
    }

    response = client.post(
        "/api/v1/experiments/compare",
        json=payload,
    )

    assert response.status_code == 422

    # --------------------------------------------------
# Benchmark analytics API tests
# --------------------------------------------------

def test_get_experiment_analytics_successfully(client):
    create_response = client.post(
        "/api/v1/experiments",
        json={
            "name": "Analytics Test",
            "description": "Test benchmark analytics",
            "scenarios": [
                {
                    "name": "Normal Execution",
                    "failure_sequence": ["none"],
                    "expected_status": "success",
                }
            ],
        },
    )

    assert create_response.status_code == 201

    experiment_id = create_response.json()["experiment_id"]

    run_response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )

    assert run_response.status_code == 200

    response = client.get(
        f"/api/v1/experiments/{experiment_id}/analytics"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["experiment_id"] == experiment_id
    assert data["total_scenarios"] == 1
    assert data["passed_scenarios"] + data["failed_scenarios"] == 1
    assert 0.0 <= data["success_rate"] <= 1.0
    assert 0.0 <= data["failure_rate"] <= 1.0
    assert data["average_latency_ms"] >= 0.0
    assert data["p50_latency_ms"] >= 0.0
    assert data["p90_latency_ms"] >= 0.0
    assert data["p95_latency_ms"] >= 0.0
    assert data["p99_latency_ms"] >= 0.0


def test_get_analytics_without_execution_results(client):
    create_response = client.post(
        "/api/v1/experiments",
        json={
            "name": "No Results Test",
            "description": "Test missing execution results",
            "scenarios": [
                {
                    "name": "Normal Execution",
                    "failure_sequence": ["none"],
                    "expected_status": "success",
                }
            ],
        },
    )

    assert create_response.status_code == 201

    experiment_id = create_response.json()["experiment_id"]

    response = client.get(
        f"/api/v1/experiments/{experiment_id}/analytics"
    )

    assert response.status_code == 404


def test_get_analytics_for_nonexistent_experiment(client):
    response = client.get(
        "/api/v1/experiments/nonexistent-id/analytics"
    )

    assert response.status_code == 404


# --------------------------------------------------
# Benchmark report API tests
# --------------------------------------------------

def test_generate_benchmark_report_successfully(client):
    create_response = client.post(
        "/api/v1/experiments",
        json={
            "name": "Report Generation Test",
            "description": "Testing benchmark report generation",
            "scenarios": [
                {
                    "name": "Normal Execution",
                    "failure_sequence": ["none"],
                    "expected_status": "success",
                }
            ],
        },
    )

    assert create_response.status_code == 201
    experiment_id = create_response.json()["experiment_id"]

    run_response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )

    assert run_response.status_code == 200

    response = client.post(
        f"/api/v1/experiments/{experiment_id}/report"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["experiment_id"] == experiment_id
    assert data["experiment_name"] == "Report Generation Test"
    assert data["total_scenarios"] == 1
    assert len(data["scenario_reports"]) == 1


def test_generate_report_without_execution_results(client):
    create_response = client.post(
        "/api/v1/experiments",
        json={
            "name": "No Execution Report Test",
            "description": "Testing missing execution results",
            "scenarios": [
                {
                    "name": "Normal Execution",
                    "failure_sequence": ["none"],
                    "expected_status": "success",
                }
            ],
        },
    )

    assert create_response.status_code == 201
    experiment_id = create_response.json()["experiment_id"]

    response = client.post(
        f"/api/v1/experiments/{experiment_id}/report"
    )

    assert response.status_code == 404


def test_get_saved_benchmark_report(client):
    create_response = client.post(
        "/api/v1/experiments",
        json={
            "name": "Saved Report Test",
            "description": "Testing report retrieval",
            "scenarios": [
                {
                    "name": "Normal Execution",
                    "failure_sequence": ["none"],
                    "expected_status": "success",
                }
            ],
        },
    )

    assert create_response.status_code == 201
    experiment_id = create_response.json()["experiment_id"]

    run_response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )

    assert run_response.status_code == 200

    generate_response = client.post(
        f"/api/v1/experiments/{experiment_id}/report"
    )

    assert generate_response.status_code == 200

    response = client.get(
        f"/api/v1/experiments/{experiment_id}/report"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["experiment_id"] == experiment_id
    assert data["experiment_name"] == "Saved Report Test"


def test_export_benchmark_report_json(client):
    create_response = client.post(
        "/api/v1/experiments",
        json={
            "name": "JSON Export Test",
            "description": "Testing JSON report export",
            "scenarios": [
                {
                    "name": "Normal Execution",
                    "failure_sequence": ["none"],
                    "expected_status": "success",
                }
            ],
        },
    )

    assert create_response.status_code == 201
    experiment_id = create_response.json()["experiment_id"]

    run_response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )

    assert run_response.status_code == 200

    generate_response = client.post(
        f"/api/v1/experiments/{experiment_id}/report"
    )

    assert generate_response.status_code == 200

    response = client.get(
        f"/api/v1/experiments/{experiment_id}/report/json"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["experiment_id"] == experiment_id
    assert "scenario_reports" in data


def test_get_nonexistent_benchmark_report(client):
    response = client.get(
        "/api/v1/experiments/nonexistent-id/report"
    )

    assert response.status_code == 404


def test_export_nonexistent_benchmark_report(client):
    response = client.get(
        "/api/v1/experiments/nonexistent-id/report/json"
    )

    assert response.status_code == 404

# --------------------------------------------------
# Day 37 - Recommendation API tests
# --------------------------------------------------

def test_generate_recommendations_successfully(client):
    create_response = client.post(
        "/api/v1/experiments",
        json={
            "name": "Recommendation API Test",
            "description": "Testing recommendation generation",
            "scenarios": [
                {
                    "name": "Normal Execution",
                    "failure_sequence": ["none"],
                    "expected_status": "success",
                }
            ],
        },
    )

    assert create_response.status_code == 201
    experiment_id = create_response.json()["experiment_id"]

    run_response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )
    assert run_response.status_code == 200

    report_response = client.post(
        f"/api/v1/experiments/{experiment_id}/report"
    )
    assert report_response.status_code == 200

    response = client.post(
        f"/api/v1/recommendations/generate/{experiment_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["experiment_id"] == experiment_id
    assert data["total_generated"] >= 1
    assert len(data["recommendations"]) >= 1


def test_generate_recommendations_for_nonexistent_experiment(client):
    response = client.post(
        "/api/v1/recommendations/generate/nonexistent-id"
    )

    assert response.status_code == 404


def test_list_recommendations(client):
    response = client.get("/api/v1/recommendations")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_recommendation_summary(client):
    response = client.get(
        "/api/v1/recommendations/summary"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_recommendations"] == 0
    assert data["open"] == 0
    assert data["in_progress"] == 0
    assert data["resolved"] == 0


def test_get_nonexistent_recommendation(client):
    response = client.get(
        "/api/v1/recommendations/nonexistent-id"
    )

    assert response.status_code == 404


def test_filter_recommendations_by_invalid_priority(client):
    response = client.get(
        "/api/v1/recommendations",
        params={"priority": "invalid"},
    )

    assert response.status_code == 422

# --------------------------------------------------
# Day 38 - Historical Insights API tests
# --------------------------------------------------

def create_completed_experiment_with_report(client, name):
    """Create an experiment, execute it and save its benchmark report."""

    create_response = client.post(
        "/api/v1/experiments",
        json={
            "name": name,
            "description": "Historical insights API test",
            "scenarios": [
                {
                    "name": "Normal Execution",
                    "failure_sequence": ["none"],
                    "expected_status": "success",
                }
            ],
        },
    )

    assert create_response.status_code == 201
    experiment_id = create_response.json()["experiment_id"]

    run_response = client.post(
        f"/api/v1/experiments/{experiment_id}/run"
    )
    assert run_response.status_code == 200

    report_response = client.post(
        f"/api/v1/experiments/{experiment_id}/report"
    )
    assert report_response.status_code == 200

    return experiment_id


def test_get_experiment_insights(client):
    experiment_id = create_completed_experiment_with_report(
        client, "Historical Insights Test"
    )

    response = client.get(f"/api/v1/insights/{experiment_id}")

    assert response.status_code == 200

    data = response.json()
    assert data["experiment_id"] == experiment_id
    assert data["reliability_score"] >= 0
    assert data["risk_level"] in ["low", "medium", "high"]
    assert "issues" in data
    assert "recommendations" in data


def test_get_insights_for_nonexistent_experiment(client):
    response = client.get("/api/v1/insights/nonexistent-id")
    assert response.status_code == 404


def test_get_all_experiment_insights(client):
    create_completed_experiment_with_report(
        client, "Historical Experiment One"
    )
    create_completed_experiment_with_report(
        client, "Historical Experiment Two"
    )

    response = client.get("/api/v1/insights")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_success_rate_trend(client):
    create_completed_experiment_with_report(
        client, "Success Trend Test"
    )

    response = client.get("/api/v1/insights/trends/success")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "success_rate" in response.json()[0]


def test_get_latency_trend(client):
    create_completed_experiment_with_report(
        client, "Latency Trend Test"
    )

    response = client.get("/api/v1/insights/trends/latency")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "average_latency_ms" in response.json()[0]


def test_get_retry_trend(client):
    create_completed_experiment_with_report(
        client, "Retry Trend Test"
    )

    response = client.get("/api/v1/insights/trends/retries")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "total_retries" in response.json()[0]


def test_get_fallback_trend(client):
    create_completed_experiment_with_report(
        client, "Fallback Trend Test"
    )

    response = client.get("/api/v1/insights/trends/fallbacks")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "total_fallbacks" in response.json()[0]


def test_get_best_experiment(client):
    create_completed_experiment_with_report(
        client, "Best Experiment Test"
    )

    response = client.get("/api/v1/insights/best")

    assert response.status_code == 200
    assert response.json()["experiment_name"] == "Best Experiment Test"


def test_get_worst_experiment(client):
    create_completed_experiment_with_report(
        client, "Worst Experiment Test"
    )

    response = client.get("/api/v1/insights/worst")

    assert response.status_code == 200
    assert response.json()["experiment_name"] == "Worst Experiment Test"


def test_get_historical_summary(client):
    create_completed_experiment_with_report(
        client, "Historical Summary Test"
    )

    response = client.get("/api/v1/insights/summary")

    assert response.status_code == 200

    data = response.json()
    assert data["total_experiments"] == 1
    assert data["average_success_rate"] >= 0
    assert data["total_retries"] >= 0
    assert data["total_fallbacks"] >= 0


def test_compare_historical_experiments(client):
    first_id = create_completed_experiment_with_report(
        client, "Comparison Experiment One"
    )
    second_id = create_completed_experiment_with_report(
        client, "Comparison Experiment Two"
    )

    response = client.get(
        "/api/v1/insights/compare",
        params={
            "first_experiment_id": first_id,
            "second_experiment_id": second_id,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["first_experiment"] == "Comparison Experiment One"
    assert data["second_experiment"] == "Comparison Experiment Two"
    assert "success_rate_difference" in data


def test_compare_nonexistent_historical_experiments(client):
    response = client.get(
        "/api/v1/insights/compare",
        params={
            "first_experiment_id": "missing-one",
            "second_experiment_id": "missing-two",
        },
    )

    assert response.status_code == 404