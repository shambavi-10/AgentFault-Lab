
import os
import uuid

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from api.main import app
from api.execution_analytics_dependencies import (
    get_execution_analytics_service,
    get_execution_reliability_service,
)
from agentfault.database.repositories.tenant_repository import TenantRepository
from agentfault.services.experiment_service import ExperimentService
from agentfault.services.execution_analytics_service import ExecutionAnalyticsService
from agentfault.services.execution_reliability_service import ExecutionReliabilityService
from agentfault.scenarios import FailureScenario


load_dotenv(".env")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def analytics_api_environment():
    """Create an isolated database-backed analytics API environment."""

    if not TEST_DATABASE_URL:
        pytest.fail("TEST_DATABASE_URL is not configured.")

    if make_url(TEST_DATABASE_URL).database != "agentfault_test":
        pytest.fail("Refusing to use a non-test database.")

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    with engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

    if database_name != "agentfault_test":
        engine.dispose()
        pytest.fail("Connected database is not agentfault_test.")

    session = Session(engine)

    tenant = TenantRepository().create(
        session,
        f"Execution Analytics API Test {uuid.uuid4()}",
    )

    tenant_id = str(tenant.tenant_id)

    experiment_service = ExperimentService(
        session=session,
        tenant_id=tenant_id,
    )

    analytics_service = ExecutionAnalyticsService(
        session=session,
        tenant_id=tenant_id,
    )

    reliability_service = ExecutionReliabilityService(
        session=session,
        tenant_id=tenant_id,
    )

    app.dependency_overrides[
        get_execution_analytics_service
    ] = lambda: analytics_service

    app.dependency_overrides[
        get_execution_reliability_service
    ] = lambda: reliability_service

    try:
        with TestClient(app) as client:
            yield {
                "client": client,
                "experiment_service": experiment_service,
                "analytics_service": analytics_service,
                "reliability_service": reliability_service,
                "tenant_id": tenant_id,
            }

    finally:
        app.dependency_overrides.pop(
            get_execution_analytics_service,
            None,
        )

        app.dependency_overrides.pop(
            get_execution_reliability_service,
            None,
        )

        session.rollback()

        from agentfault.database.models.tenant import TenantModel

        tenant_model = session.get(TenantModel, tenant.tenant_id)

        if tenant_model is not None:
            session.delete(tenant_model)
            session.commit()

        session.close()
        engine.dispose()


@pytest.fixture
def analytics_api_with_execution(analytics_api_environment):
    """Create an experiment and persist one successful execution."""

    environment = analytics_api_environment

    service = environment["experiment_service"]

    experiment = service.create_experiment(
        name=f"Analytics API Test {uuid.uuid4()}",
        description="Testing execution analytics endpoints.",
        scenarios=[
            FailureScenario(
                name="Successful analytics scenario",
                failure_sequence=["none"],
                expected_status="success",
            )
        ],
    )

    service.run_experiment(experiment.experiment_id)

    return environment
def test_execution_overview_returns_persisted_metrics(
    analytics_api_with_execution,
):
    client = analytics_api_with_execution["client"]

    response = client.get(
        "/api/v1/execution-analytics/overview"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_runs"] == 1
    assert data["completed_runs"] == 1
    assert data["failed_runs"] == 0
    assert data["total_scenarios"] == 1
    assert data["average_success_rate"] == 1
    assert data["total_retries"] == 0


def test_success_trend_returns_persisted_execution(
    analytics_api_with_execution,
):
    client = analytics_api_with_execution["client"]

    response = client.get(
        "/api/v1/execution-analytics/trends/success"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["success_rate"] == 1
    assert data[0]["passed_scenarios"] == 1
    assert data[0]["failed_scenarios"] == 0


def test_latency_trend_returns_execution_metrics(
    analytics_api_with_execution,
):
    client = analytics_api_with_execution["client"]

    response = client.get(
        "/api/v1/execution-analytics/trends/latency"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["total_execution_time_ms"] >= 0
    assert data[0]["average_scenario_time_ms"] >= 0
    assert data[0]["slowest_scenario_name"] == (
        "Successful analytics scenario"
    )
def test_retry_trend_returns_execution_metrics(
    analytics_api_with_execution,
):
    client = analytics_api_with_execution["client"]

    response = client.get(
        "/api/v1/execution-analytics/trends/retries"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["total_retries"] == 0
    assert data[0]["average_retries_per_scenario"] == 0


def test_fallback_trend_returns_execution_metrics(
    analytics_api_with_execution,
):
    client = analytics_api_with_execution["client"]

    response = client.get(
        "/api/v1/execution-analytics/trends/fallbacks"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["total_fallbacks"] == 0
    assert data[0]["fallback_used"] is False


def test_circuit_breaker_trend_returns_execution_metrics(
    analytics_api_with_execution,
):
    client = analytics_api_with_execution["client"]

    response = client.get(
        "/api/v1/execution-analytics/trends/circuit-breaker"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["total_scenarios"] == 1
    assert data[0]["circuit_breaker_enabled_scenarios"] == 0
    assert data[0]["circuit_breaker_enabled_percentage"] == 0


def test_reliability_endpoint_returns_summary(
    analytics_api_with_execution,
):
    client = analytics_api_with_execution["client"]

    response = client.get(
        "/api/v1/execution-analytics/reliability"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_runs"] == 1
    assert data["total_scenarios"] == 1
    assert data["success_rate"] == 1
    assert data["reliability_score"] > 0
    assert data["risk_level"] in ["low", "medium", "high"]
    assert "success" in data["metric_scores"]
    assert "latency" in data["metric_scores"]
    assert "retry" in data["metric_scores"]
    assert "fallback" in data["metric_scores"]
    assert isinstance(data["recommendations"], list)

def test_empty_execution_overview_returns_zero_metrics(
    analytics_api_environment,
):
    client = analytics_api_environment["client"]

    response = client.get(
        "/api/v1/execution-analytics/overview"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_runs"] == 0
    assert data["completed_runs"] == 0
    assert data["failed_runs"] == 0
    assert data["total_scenarios"] == 0
    assert data["average_success_rate"] == 0
    assert data["average_execution_time_ms"] == 0
    assert data["total_retries"] == 0


def test_empty_execution_reliability_returns_unknown(
    analytics_api_environment,
):
    client = analytics_api_environment["client"]

    response = client.get(
        "/api/v1/execution-analytics/reliability"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_runs"] == 0
    assert data["total_scenarios"] == 0
    assert data["reliability_score"] == 0
    assert data["risk_level"] == "unknown"
    assert data["issues"]
    assert data["recommendations"]

def test_execution_analytics_isolated_between_tenants(
    analytics_api_environment,
):
    environment = analytics_api_environment
    client = environment["client"]
    service = environment["experiment_service"]

    experiment = service.create_experiment(
        name=f"Tenant Isolation Test {uuid.uuid4()}",
        scenarios=[
            FailureScenario(
                name="Tenant A scenario",
                failure_sequence=["none"],
                expected_status="success",
            )
        ],
    )

    service.run_experiment(experiment.experiment_id)

    response = client.get(
        "/api/v1/execution-analytics/overview"
    )

    assert response.status_code == 200
    assert response.json()["total_runs"] == 1

    other_tenant_id = str(uuid.uuid4())

    other_analytics_service = ExecutionAnalyticsService(
        session=service.session,
        tenant_id=other_tenant_id,
    )

    other_overview = other_analytics_service.get_execution_overview()

    assert other_overview["total_runs"] == 0
    assert other_overview["total_scenarios"] == 0