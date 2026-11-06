
import os
import uuid

import pytest
from dotenv import load_dotenv
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from agentfault.database.base import Base
from agentfault.database.models.experiment import ExperimentModel
from agentfault.database.models.experiment_scenario import (
    ExperimentScenarioModel,
)
from agentfault.database.models.tenant import TenantModel
from agentfault.database.repositories.experiment_repository import (
    ExperimentRepository,
)
from agentfault.database.repositories.tenant_repository import (
    TenantRepository,
)

from agentfault.experiment import Experiment
from agentfault.reliability_config import ReliabilityConfig
from agentfault.scenarios import FailureScenario


load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")



@pytest.fixture(scope="module", autouse=True)
def verify_test_database():
    """Ensure repository tests use only the test database."""

    if not TEST_DATABASE_URL:
        pytest.fail("TEST_DATABASE_URL is not configured.")

    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    if make_url(TEST_DATABASE_URL).database != "agentfault_test":
        pytest.fail(
            "Database tests must run against agentfault_test only."
        )

    test_engine = create_engine(TEST_DATABASE_URL)

    try:
        with test_engine.connect() as connection:
            current_database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

        if current_database != "agentfault_test":
            pytest.fail(
                "Connected database is not agentfault_test."
            )
    finally:
        test_engine.dispose()


@pytest.fixture
def db_session():
    """Provide an isolated session for each repository test."""

    from sqlalchemy import create_engine

    from sqlalchemy.engine import make_url

    test_engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    if make_url(str(test_engine.url)).database != "agentfault_test":
        test_engine.dispose()
        pytest.fail("Refusing to use a non-test database.")

    with test_engine.begin() as connection:
        connection.execute(
            delete(ExperimentScenarioModel)
        )
        connection.execute(delete(ExperimentModel))
        connection.execute(delete(TenantModel))

    session = Session(test_engine)

    try:
        yield session
    finally:
        session.close()

        with test_engine.begin() as connection:
            connection.execute(
                delete(ExperimentScenarioModel)
            )
            connection.execute(delete(ExperimentModel))
            connection.execute(delete(TenantModel))

        test_engine.dispose()


@pytest.fixture
def tenant_repository():
    return TenantRepository()


@pytest.fixture
def experiment_repository():
    return ExperimentRepository()


@pytest.fixture
def tenant(db_session, tenant_repository):
    return tenant_repository.create(
        db_session,
        "Test Organization",
    )


def make_scenario(
    name="Timeout scenario",
    failure_sequence=None,
    expected_status="success",
):
    return FailureScenario(
        name=name,
        failure_sequence=failure_sequence or ["timeout", "none"],
        expected_status=expected_status,
    )


def make_experiment():
    return Experiment(
        name="Database Test Experiment",
        description="Testing PostgreSQL persistence",
        scenarios=[
            make_scenario("First scenario"),
            make_scenario(
                "Second scenario",
                ["rate_limit", "none"],
                "failure",
            ),
        ],
        reliability_config=ReliabilityConfig(
            max_attempts=5,
            retry_strategy="exponential",
            base_delay=2.0,
            max_delay=20.0,
            jitter=True,
            enable_circuit_breaker=True,
            failure_threshold=4,
            recovery_timeout=15.0,
            enable_fallback=True,
        ),
    )


# --------------------------------------------------
# TENANT REPOSITORY TESTS
# --------------------------------------------------

def test_create_tenant(
    db_session,
    tenant_repository,
):
    tenant = tenant_repository.create(
        db_session,
        "Organization A",
    )

    assert tenant.name == "Organization A"
    assert isinstance(tenant.tenant_id, uuid.UUID)


def test_create_tenant_rejects_empty_name(
    db_session,
    tenant_repository,
):
    with pytest.raises(ValueError, match="cannot be empty"):
        tenant_repository.create(db_session, "   ")


def test_get_tenant_by_id(
    db_session,
    tenant_repository,
    tenant,
):
    retrieved = tenant_repository.get_by_id(
        db_session,
        tenant.tenant_id,
    )

    assert retrieved is not None
    assert retrieved.tenant_id == tenant.tenant_id


def test_get_tenant_rejects_invalid_uuid(
    db_session,
    tenant_repository,
):
    with pytest.raises(ValueError, match="Invalid tenant UUID"):
        tenant_repository.get_by_id(
            db_session,
            "invalid-id",
        )


def test_list_tenants(
    db_session,
    tenant_repository,
):
    tenant_repository.create(db_session, "Organization A")
    tenant_repository.create(db_session, "Organization B")

    tenants = tenant_repository.list_all(db_session)

    assert len(tenants) == 2


# --------------------------------------------------
# EXPERIMENT PERSISTENCE TESTS
# --------------------------------------------------

def test_create_experiment(
    db_session,
    tenant,
    experiment_repository,
):
    experiment = make_experiment()

    saved = experiment_repository.create(
        db_session,
        experiment,
        tenant.tenant_id,
    )

    assert saved.experiment_id == experiment.experiment_id
    assert saved.name == experiment.name
    assert saved.status == "pending"


def test_get_experiment_by_id(
    db_session,
    tenant,
    experiment_repository,
):
    experiment = make_experiment()

    experiment_repository.create(
        db_session,
        experiment,
        tenant.tenant_id,
    )

    retrieved = experiment_repository.get_by_id(
        db_session,
        experiment.experiment_id,
        tenant.tenant_id,
    )

    assert retrieved is not None
    assert retrieved.experiment_id == experiment.experiment_id


def test_experiment_scenarios_preserve_order(
    db_session,
    tenant,
    experiment_repository,
):
    experiment = make_experiment()

    experiment_repository.create(
        db_session,
        experiment,
        tenant.tenant_id,
    )

    retrieved = experiment_repository.get_by_id(
        db_session,
        experiment.experiment_id,
        tenant.tenant_id,
    )

    assert retrieved is not None
    assert len(retrieved.scenarios) == 2
    assert retrieved.scenarios[0].name == "First scenario"
    assert retrieved.scenarios[1].name == "Second scenario"


def test_reliability_config_round_trip(
    db_session,
    tenant,
    experiment_repository,
):
    experiment = make_experiment()

    experiment_repository.create(
        db_session,
        experiment,
        tenant.tenant_id,
    )

    retrieved = experiment_repository.get_by_id(
        db_session,
        experiment.experiment_id,
        tenant.tenant_id,
    )

    assert retrieved is not None
    assert retrieved.reliability_config == experiment.reliability_config


def test_list_experiments_by_tenant(
    db_session,
    tenant,
    experiment_repository,
):
    first = make_experiment()
    second = make_experiment()

    second.name = "Second Database Experiment"

    experiment_repository.create(
        db_session,
        first,
        tenant.tenant_id,
    )

    experiment_repository.create(
        db_session,
        second,
        tenant.tenant_id,
    )

    experiments = experiment_repository.list_by_tenant(
        db_session,
        tenant.tenant_id,
    )

    assert len(experiments) == 2


# --------------------------------------------------
# TENANT ISOLATION TESTS
# --------------------------------------------------

def test_experiment_is_not_visible_to_another_tenant(
    db_session,
    tenant_repository,
    experiment_repository,
):
    tenant_a = tenant_repository.create(
        db_session,
        "Tenant A",
    )

    tenant_b = tenant_repository.create(
        db_session,
        "Tenant B",
    )

    experiment = make_experiment()

    experiment_repository.create(
        db_session,
        experiment,
        tenant_a.tenant_id,
    )

    retrieved = experiment_repository.get_by_id(
        db_session,
        experiment.experiment_id,
        tenant_b.tenant_id,
    )

    assert retrieved is None


def test_experiment_listing_is_tenant_scoped(
    db_session,
    tenant_repository,
    experiment_repository,
):
    tenant_a = tenant_repository.create(
        db_session,
        "Tenant A",
    )

    tenant_b = tenant_repository.create(
        db_session,
        "Tenant B",
    )

    experiment_repository.create(
        db_session,
        make_experiment(),
        tenant_a.tenant_id,
    )

    experiments = experiment_repository.list_by_tenant(
        db_session,
        tenant_b.tenant_id,
    )

    assert experiments == []


# --------------------------------------------------
# STATUS AND DELETION TESTS
# --------------------------------------------------

def test_update_experiment_status(
    db_session,
    tenant,
    experiment_repository,
):
    experiment = make_experiment()

    experiment_repository.create(
        db_session,
        experiment,
        tenant.tenant_id,
    )

    updated = experiment_repository.update_status(
        db_session,
        experiment.experiment_id,
        tenant.tenant_id,
        "running",
    )

    assert updated.status == "running"


def test_update_rejects_invalid_status(
    db_session,
    tenant,
    experiment_repository,
):
    experiment = make_experiment()

    experiment_repository.create(
        db_session,
        experiment,
        tenant.tenant_id,
    )

    with pytest.raises(ValueError, match="Invalid experiment status"):
        experiment_repository.update_status(
            db_session,
            experiment.experiment_id,
            tenant.tenant_id,
            "invalid",
        )


def test_delete_pending_experiment(
    db_session,
    tenant,
    experiment_repository,
):
    experiment = make_experiment()

    experiment_repository.create(
        db_session,
        experiment,
        tenant.tenant_id,
    )

    experiment_repository.delete_pending(
        db_session,
        experiment.experiment_id,
        tenant.tenant_id,
    )

    retrieved = experiment_repository.get_by_id(
        db_session,
        experiment.experiment_id,
        tenant.tenant_id,
    )

    assert retrieved is None


def test_cannot_delete_running_experiment(
    db_session,
    tenant,
    experiment_repository,
):
    experiment = make_experiment()

    experiment_repository.create(
        db_session,
        experiment,
        tenant.tenant_id,
    )

    experiment_repository.update_status(
        db_session,
        experiment.experiment_id,
        tenant.tenant_id,
        "running",
    )

    with pytest.raises(ValueError, match="Only pending"):
        experiment_repository.delete_pending(
            db_session,
            experiment.experiment_id,
            tenant.tenant_id,
        )

from agentfault.services.experiment_service import ExperimentService


# --------------------------------------------------
# EXPERIMENT SERVICE TESTS
# --------------------------------------------------

def test_service_create_and_retrieve_experiment(db_session, tenant):
    service = ExperimentService(db_session, str(tenant.tenant_id))

    created = service.create_experiment(
        name="Service Test Experiment",
        scenarios=[make_scenario()],
        description="Testing service persistence",
    )

    retrieved = service.get_experiment(created.experiment_id)

    assert retrieved.experiment_id == created.experiment_id
    assert retrieved.name == "Service Test Experiment"
    assert retrieved.status == "pending"
    assert len(retrieved.scenarios) == 1


def test_service_list_experiments_by_tenant(
    db_session, tenant, tenant_repository
):
    service = ExperimentService(db_session, str(tenant.tenant_id))

    service.create_experiment(
        name="Tenant Experiment",
        scenarios=[make_scenario()],
    )

    other_tenant = tenant_repository.create(
        db_session, "Another Organization"
    )

    other_service = ExperimentService(
        db_session, str(other_tenant.tenant_id)
    )

    other_service.create_experiment(
        name="Other Tenant Experiment",
        scenarios=[make_scenario()],
    )

    experiments = service.list_experiments()

    assert len(experiments) == 1
    assert experiments[0].name == "Tenant Experiment"


def test_service_rejects_experiment_from_another_tenant(
    db_session, tenant, tenant_repository
):
    other_tenant = tenant_repository.create(
        db_session, "Another Organization"
    )

    other_service = ExperimentService(
        db_session, str(other_tenant.tenant_id)
    )

    experiment = other_service.create_experiment(
        name="Private Experiment",
        scenarios=[make_scenario()],
    )

    service = ExperimentService(db_session, str(tenant.tenant_id))

    with pytest.raises(KeyError, match="Experiment not found"):
        service.get_experiment(experiment.experiment_id)


def test_service_delete_pending_experiment(db_session, tenant):
    service = ExperimentService(db_session, str(tenant.tenant_id))

    experiment = service.create_experiment(
        name="Delete Test",
        scenarios=[make_scenario()],
    )

    service.delete_experiment(experiment.experiment_id)

    with pytest.raises(KeyError, match="Experiment not found"):
        service.get_experiment(experiment.experiment_id)


def test_service_run_persists_completed_status(db_session, tenant):
    service = ExperimentService(db_session, str(tenant.tenant_id))

    experiment = service.create_experiment(
        name="Execution Test",
        scenarios=[
            make_scenario(
                name="Successful scenario",
                failure_sequence=["none"],
                expected_status="success",
            )
        ],
    )

    execution = service.run_experiment(experiment.experiment_id)
    persisted = service.get_experiment(experiment.experiment_id)

    assert execution.status == "completed"
    assert persisted.status == "completed"


def test_service_run_persists_failed_status(
    db_session, tenant, monkeypatch
):
    import agentfault.services.experiment_service as service_module

    service = ExperimentService(db_session, str(tenant.tenant_id))

    experiment = service.create_experiment(
        name="Failed Execution Test",
        scenarios=[make_scenario()],
    )

    def simulate_failure(experiment):
        experiment.start()
        experiment.fail()
        raise RuntimeError("Simulated execution failure")

    monkeypatch.setattr(
        service_module, "execute_experiment", simulate_failure
    )

    with pytest.raises(RuntimeError, match="Simulated execution failure"):
        service.run_experiment(experiment.experiment_id)

    persisted = service.get_experiment(experiment.experiment_id)

    assert persisted.status == "failed"

def test_service_run_persists_complete_execution_history(
    db_session, tenant
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from agentfault.database.models.experiment_run import (
        ExperimentRunModel,
    )
    from agentfault.database.models.scenario_execution_result import (
        ScenarioExecutionResultModel,
    )
    from agentfault.database.models.execution_trace_event import (
        ExecutionTraceEventModel,
    )
    from agentfault.services.experiment_service import ExperimentService

    service = ExperimentService(
        db_session,
        str(tenant.tenant_id),
    )

    experiment = service.create_experiment(
        name="Execution History Persistence Test",
        scenarios=[
            make_scenario(
                name="Normal Execution",
                failure_sequence=["none"],
                expected_status="success",
            )
        ],
    )

    execution = service.run_experiment(experiment.experiment_id)

    statement = (
        select(ExperimentRunModel)
        .where(
            ExperimentRunModel.experiment_id
            == uuid.UUID(experiment.experiment_id)
        )
        .options(
            selectinload(ExperimentRunModel.scenario_results)
            .selectinload(
                ScenarioExecutionResultModel.trace_events
            )
        )
    )

    persisted_run = db_session.scalar(statement)

    assert persisted_run is not None
    assert persisted_run.status == "completed"
    assert persisted_run.total_scenarios == 1
    assert persisted_run.passed_scenarios == 1

    assert len(persisted_run.scenario_results) == 1

    persisted_scenario = persisted_run.scenario_results[0]

    assert persisted_scenario.scenario_name == "Normal Execution"
    assert persisted_scenario.passed is True
    assert persisted_scenario.result_data["status"] == "success"

    expected_events = execution.scenario_results[0].trace.events

    assert len(persisted_scenario.trace_events) == len(expected_events)

    for persisted_event, expected_event in zip(
        persisted_scenario.trace_events,
        expected_events,
    ):
        assert persisted_event.event_type == expected_event.event_type
        assert persisted_event.execution_id == expected_event.execution_id

    assert db_session.scalar(
        select(ExperimentRunModel.run_id).where(
            ExperimentRunModel.experiment_id
            == uuid.UUID(experiment.experiment_id)
        )
    ) is not None
