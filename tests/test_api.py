
import pytest

from fastapi.testclient import TestClient

import api.main as main

from api.experiment_dependencies import get_experiment_manager
from agentfault.experiment_manager import ExperimentManager
from agentfault.dashboard_service import DashboardServiceError
from api.execution_dependencies import get_execution_results_store

@pytest.fixture
def experiment_manager():
    return ExperimentManager()

@pytest.fixture
def client(experiment_manager):
    get_execution_results_store().clear()

    main.app.dependency_overrides[get_experiment_manager] = (
        lambda: experiment_manager
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