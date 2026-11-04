
import pytest

from fastapi.testclient import TestClient

import api.main as main
from agentfault.dashboard_service import DashboardServiceError


@pytest.fixture
def client():
    return TestClient(main.app)


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
