import os
import uuid

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from agentfault.database.repositories.tenant_repository import (
    TenantRepository,
)
from agentfault.services.experiment_service import ExperimentService
from agentfault.services.execution_analytics_service import (
    ExecutionAnalyticsService,
)
from agentfault.scenarios import FailureScenario


load_dotenv(".env")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def analytics_environment():
    """Create an isolated database-backed analytics environment."""

    if not TEST_DATABASE_URL:
        pytest.fail("TEST_DATABASE_URL is not configured.")

    if make_url(TEST_DATABASE_URL).database != "agentfault_test":
        pytest.fail("Refusing to use a non-test database.")

    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

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
        f"Analytics Test {uuid.uuid4()}",
    )

    experiment_service = ExperimentService(
        session=session,
        tenant_id=str(tenant.tenant_id),
    )

    analytics_service = ExecutionAnalyticsService(
        session=session,
        tenant_id=str(tenant.tenant_id),
    )

    try:
        yield {
            "session": session,
            "tenant": tenant,
            "experiment_service": experiment_service,
            "analytics_service": analytics_service,
        }
    finally:
        from agentfault.database.models.tenant import TenantModel

        session.rollback()

        tenant_record = session.get(
            TenantModel,
            tenant.tenant_id,
        )

        if tenant_record is not None:
            session.delete(tenant_record)
            session.commit()

        session.close()
        engine.dispose()


def create_test_experiment(
    experiment_service,
    name="Analytics Test Experiment",
):
    """Create a simple experiment for analytics testing."""

    return experiment_service.create_experiment(
        name=name,
        scenarios=[
            FailureScenario(
                name="Successful scenario",
                failure_sequence=["none"],
                expected_status="success",
            )
        ],
    )

def test_empty_tenant_returns_zero_overview(
    analytics_environment,
):
    analytics_service = analytics_environment[
        "analytics_service"
    ]

    overview = analytics_service.get_execution_overview()

    assert overview == {
        "total_runs": 0,
        "completed_runs": 0,
        "failed_runs": 0,
        "total_scenarios": 0,
        "average_success_rate": 0.0,
        "average_execution_time_ms": 0.0,
        "total_retries": 0,
    }

def test_overview_with_one_execution(analytics_environment):
    experiment_service = analytics_environment[
        "experiment_service"
    ]
    analytics_service = analytics_environment[
        "analytics_service"
    ]

    experiment = create_test_experiment(experiment_service)

    experiment_service.run_experiment(experiment.experiment_id)

    overview = analytics_service.get_execution_overview()

    assert overview["total_runs"] == 1
    assert overview["completed_runs"] == 1
    assert overview["failed_runs"] == 0
    assert overview["total_scenarios"] == 1
    assert overview["average_success_rate"] == 1.0
    assert overview["average_execution_time_ms"] > 0
    assert overview["total_retries"] >= 0




def test_overview_aggregates_multiple_executions(
    analytics_environment,
):
    experiment_service = analytics_environment[
        "experiment_service"
    ]
    analytics_service = analytics_environment[
        "analytics_service"
    ]

    for index in range(3):
        experiment = create_test_experiment(
            experiment_service,
            name=f"Analytics Experiment {index}",
        )

        experiment_service.run_experiment(
            experiment.experiment_id
        )

    overview = analytics_service.get_execution_overview()

    assert overview["total_runs"] == 3
    assert overview["completed_runs"] == 3
    assert overview["failed_runs"] == 0
    assert overview["total_scenarios"] == 3
    assert overview["average_success_rate"] == 1.0
    assert overview["average_execution_time_ms"] > 0


def test_analytics_are_isolated_by_tenant(
    analytics_environment,
):
    from agentfault.database.repositories.tenant_repository import (
        TenantRepository,
    )
    from agentfault.services.experiment_service import ExperimentService
    from agentfault.services.execution_analytics_service import (
        ExecutionAnalyticsService,
    )

    environment = analytics_environment

    session = environment["session"]
    own_service = environment["experiment_service"]
    own_analytics = environment["analytics_service"]

    other_tenant = TenantRepository().create(
        session,
        f"Other Tenant {uuid.uuid4()}",
    )

    other_experiment_service = ExperimentService(
        session=session,
        tenant_id=str(other_tenant.tenant_id),
    )

    other_analytics = ExecutionAnalyticsService(
        session=session,
        tenant_id=str(other_tenant.tenant_id),
    )

    own_experiment = create_test_experiment(
        own_service,
        "Own Tenant Experiment",
    )

    other_experiment = create_test_experiment(
        other_experiment_service,
        "Other Tenant Experiment",
    )

    own_service.run_experiment(own_experiment.experiment_id)
    other_experiment_service.run_experiment(
        other_experiment.experiment_id
    )

    own_overview = own_analytics.get_execution_overview()
    other_overview = other_analytics.get_execution_overview()

    assert own_overview["total_runs"] == 1
    assert other_overview["total_runs"] == 1

    session.delete(other_tenant)
    session.commit()


def test_success_rate_trend_returns_execution_metrics(
    analytics_environment,
):
    experiment_service = analytics_environment[
        "experiment_service"
    ]
    analytics_service = analytics_environment[
        "analytics_service"
    ]

    experiment = create_test_experiment(experiment_service)

    experiment_service.run_experiment(experiment.experiment_id)

    trend = analytics_service.get_success_rate_trend()

    assert len(trend) == 1
    assert trend[0]["success_rate"] == 1.0
    assert trend[0]["passed_scenarios"] == 1
    assert trend[0]["failed_scenarios"] == 0
    assert "run_id" in trend[0]
    assert "created_at" in trend[0]

def test_success_rate_trend_is_chronological(
    analytics_environment,
):
    experiment_service = analytics_environment[
        "experiment_service"
    ]
    analytics_service = analytics_environment[
        "analytics_service"
    ]

    for index in range(3):
        experiment = create_test_experiment(
            experiment_service,
            name=f"Trend Experiment {index}",
        )
        experiment_service.run_experiment(
            experiment.experiment_id
        )

    trend = analytics_service.get_success_rate_trend()

    assert len(trend) == 3

    timestamps = [
        item["created_at"] for item in trend
    ]

    assert timestamps == sorted(timestamps)

def test_latency_trend_returns_execution_metrics(
    analytics_environment,
):
    experiment_service = analytics_environment[
        "experiment_service"
    ]
    analytics_service = analytics_environment[
        "analytics_service"
    ]

    experiment = create_test_experiment(experiment_service)

    experiment_service.run_experiment(experiment.experiment_id)

    trend = analytics_service.get_latency_trend()

    assert len(trend) == 1
    assert trend[0]["total_execution_time_ms"] > 0
    assert trend[0]["average_scenario_time_ms"] > 0
    assert trend[0]["slowest_scenario_time_ms"] > 0
    assert trend[0]["slowest_scenario_name"] == (
        "Successful scenario"
    )
    assert "run_id" in trend[0]
    assert "created_at" in trend[0]

    
def test_retry_trend_returns_execution_metrics(
    analytics_environment,
):
    experiment_service = analytics_environment[
        "experiment_service"
    ]
    analytics_service = analytics_environment[
        "analytics_service"
    ]

    experiment = create_test_experiment(experiment_service)

    experiment_service.run_experiment(experiment.experiment_id)

    trend = analytics_service.get_retry_trend()

    assert len(trend) == 1
    assert trend[0]["total_retries"] >= 0
    assert trend[0]["average_retries_per_scenario"] >= 0
    assert trend[0]["max_retries"] >= 0
    assert trend[0]["max_retry_scenario_name"] == (
        "Successful scenario"
    )
    assert "run_id" in trend[0]
    assert "created_at" in trend[0]

def test_fallback_trend_returns_execution_metrics(
    analytics_environment,
):
    experiment_service = analytics_environment[
        "experiment_service"
    ]
    analytics_service = analytics_environment[
        "analytics_service"
    ]

    experiment = create_test_experiment(experiment_service)

    experiment_service.run_experiment(experiment.experiment_id)

    trend = analytics_service.get_fallback_trend()

    assert len(trend) == 1
    assert trend[0]["total_fallbacks"] >= 0
    assert trend[0]["average_fallbacks_per_scenario"] >= 0
    assert trend[0]["max_fallbacks"] >= 0
    assert trend[0]["max_fallback_scenario_name"] == (
        "Successful scenario"
    )
    assert isinstance(trend[0]["fallback_used"], bool)
    assert "run_id" in trend[0]
    assert "created_at" in trend[0]


def test_circuit_breaker_trend_returns_execution_metrics(
    analytics_environment,
):
    experiment_service = analytics_environment[
        "experiment_service"
    ]
    analytics_service = analytics_environment[
        "analytics_service"
    ]

    experiment = create_test_experiment(experiment_service)

    experiment_service.run_experiment(experiment.experiment_id)

    trend = analytics_service.get_circuit_breaker_trend()

    assert len(trend) == 1
    assert trend[0]["total_scenarios"] == 1
    assert trend[0]["circuit_breaker_enabled_scenarios"] >= 0
    assert (
        0
        <= trend[0]["circuit_breaker_enabled_percentage"]
        <= 100
    )
    assert "run_id" in trend[0]
    assert "created_at" in trend[0]
