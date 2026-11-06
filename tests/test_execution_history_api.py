import os
import uuid

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from api.main import app
from api.experiment_dependencies import get_experiment_manager

from agentfault.database.repositories.tenant_repository import TenantRepository
from agentfault.services.experiment_service import ExperimentService
from agentfault.scenarios import FailureScenario


load_dotenv(".env")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def api_environment():
    """Create an isolated database-backed API environment."""

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
        f"Execution API Test {uuid.uuid4()}",
    )

    service = ExperimentService(
        session=session,
        tenant_id=str(tenant.tenant_id),
    )

    app.dependency_overrides[get_experiment_manager] = lambda: service

    try:
        with TestClient(app) as client:
            yield client, service
    finally:
        app.dependency_overrides.pop(
            get_experiment_manager,
            None,
        )

        session.rollback()

        from agentfault.database.models.tenant import TenantModel

        session.delete(
            session.get(TenantModel, tenant.tenant_id)
        )
        session.commit()

        session.close()
        engine.dispose()


@pytest.fixture
def executed_experiment(api_environment):
    """Create and execute an experiment with persisted history."""

    client, service = api_environment

    experiment = service.create_experiment(
        name=f"Execution History Test {uuid.uuid4()}",
        description="Testing persistent execution history API.",
        scenarios=[
            FailureScenario(
                name="Successful scenario",
                failure_sequence=["none"],
                expected_status="success",
            )
        ],
    )

    service.run_experiment(experiment.experiment_id)

    runs = service.execution_repository.list_by_experiment(
        service.session,
        experiment.experiment_id,
        service.tenant_id,
    )

    assert len(runs) == 1

    return client, service, experiment, runs[0]


def test_list_persistent_execution_runs(executed_experiment):
    client, service, experiment, run = executed_experiment

    response = client.get(
        f"/api/v1/experiments/{experiment.experiment_id}/runs"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["run_id"] == str(run.run_id)
    assert data[0]["experiment_id"] == experiment.experiment_id
    assert data[0]["total_scenarios"] == 1


def test_get_persistent_execution_run_details(executed_experiment):
    client, service, experiment, run = executed_experiment

    response = client.get(
        f"/api/v1/experiments/{experiment.experiment_id}"
        f"/runs/{run.run_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["run_id"] == str(run.run_id)
    assert len(data["scenario_results"]) == 1
    assert data["scenario_results"][0]["scenario_name"] == (
        "Successful scenario"
    )


def test_get_persistent_execution_traces(executed_experiment):
    client, service, experiment, run = executed_experiment

    response = client.get(
        f"/api/v1/experiments/{experiment.experiment_id}"
        f"/runs/{run.run_id}/traces"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["scenario_name"] == "Successful scenario"
    assert isinstance(data[0]["trace_events"], list)
    assert len(data[0]["trace_events"]) > 0


def test_nonexistent_execution_run_returns_404(executed_experiment):
    client, service, experiment, run = executed_experiment

    nonexistent_run_id = str(uuid.uuid4())

    response = client.get(
        f"/api/v1/experiments/{experiment.experiment_id}"
        f"/runs/{nonexistent_run_id}"
    )

    assert response.status_code == 404


def test_run_from_another_experiment_returns_404(
    executed_experiment,
):
    client, service, experiment, run = executed_experiment

    another_experiment = service.create_experiment(
        name=f"Another Experiment {uuid.uuid4()}",
        scenarios=[
            FailureScenario(
                name="Another scenario",
                failure_sequence=["none"],
                expected_status="success",
            )
        ],
    )

    response = client.get(
        f"/api/v1/experiments/{another_experiment.experiment_id}"
        f"/runs/{run.run_id}"
    )

    assert response.status_code == 404


def test_cross_tenant_execution_run_access_returns_404(
    executed_experiment,
):
    client, service, experiment, run = executed_experiment

    original_tenant_id = service.tenant_id

    other_tenant = TenantRepository().create(
        service.session,
        f"Other Tenant {uuid.uuid4()}",
    )

    try:
        service.tenant_id = str(other_tenant.tenant_id)

        response = client.get(
            f"/api/v1/experiments/{experiment.experiment_id}"
            f"/runs/{run.run_id}"
        )

        assert response.status_code == 404

    finally:
        service.tenant_id = original_tenant_id

        service.session.delete(other_tenant)
        service.session.commit()
