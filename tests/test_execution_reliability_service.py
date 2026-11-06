
import os
import uuid

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from agentfault.reliability_config import ReliabilityConfig

from agentfault.database.repositories.tenant_repository import (
    TenantRepository,
)
from agentfault.database.models.tenant import TenantModel
from agentfault.services.experiment_service import ExperimentService
from agentfault.services.execution_reliability_service import (
    ExecutionReliabilityService,
)
from agentfault.scenarios import FailureScenario
from agentfault.experiment_executor import execute_experiment
from agentfault.faults import simulated_tool


load_dotenv(".env")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def reliability_environment():
    """Create an isolated database-backed reliability environment."""

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
        f"Reliability Test {uuid.uuid4()}",
    )

    experiment_service = ExperimentService(
        session=session,
        tenant_id=str(tenant.tenant_id),
    )

    reliability_service = ExecutionReliabilityService(
        session=session,
        tenant_id=str(tenant.tenant_id),
    )

    try:
        yield {
            "session": session,
            "tenant": tenant,
            "experiment_service": experiment_service,
            "reliability_service": reliability_service,
        }

    finally:
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


def create_reliability_experiment(
    experiment_service,
    name="Reliability Test Experiment",
):
    """Create a simple successful experiment."""

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


def test_empty_tenant_returns_unknown_reliability(
    reliability_environment,
):
    service = reliability_environment["reliability_service"]

    summary = service.generate_reliability_summary()

    assert summary["total_runs"] == 0
    assert summary["total_scenarios"] == 0
    assert summary["reliability_score"] == 0.0
    assert summary["risk_level"] == "unknown"
    assert summary["issues"] == [
        "No execution history available"
    ]


def test_one_successful_execution_returns_reliability_summary(
    reliability_environment,
):
    experiment_service = reliability_environment[
        "experiment_service"
    ]
    service = reliability_environment["reliability_service"]

    experiment = create_reliability_experiment(
        experiment_service
    )

    experiment_service.run_experiment(experiment.experiment_id)

    summary = service.generate_reliability_summary()

    assert summary["total_runs"] == 1
    assert summary["total_scenarios"] == 1
    assert 0 <= summary["reliability_score"] <= 100
    assert summary["risk_level"] in [
        "low",
        "medium",
        "high",
    ]
    assert summary["success_rate"] == 1.0


def test_multiple_executions_are_aggregated(
    reliability_environment,
):
    experiment_service = reliability_environment[
        "experiment_service"
    ]
    service = reliability_environment["reliability_service"]

    for index in range(3):
        experiment = create_reliability_experiment(
            experiment_service,
            name=f"Reliability Experiment {index}",
        )

        experiment_service.run_experiment(
            experiment.experiment_id
        )

    summary = service.generate_reliability_summary()

    assert summary["total_runs"] == 3
    assert summary["total_scenarios"] == 3
    assert summary["success_rate"] == 1.0
    assert summary["average_latency_ms"] > 0


def test_reliability_summary_contains_metric_scores(
    reliability_environment,
):
    experiment_service = reliability_environment[
        "experiment_service"
    ]
    service = reliability_environment["reliability_service"]

    experiment = create_reliability_experiment(
        experiment_service
    )

    experiment_service.run_experiment(experiment.experiment_id)

    summary = service.generate_reliability_summary()

    scores = summary["metric_scores"]

    assert set(scores) == {
        "success",
        "latency",
        "retry",
        "fallback",
    }

    assert all(
        0 <= score <= maximum
        for score, maximum in [
            (scores["success"], 50),
            (scores["latency"], 20),
            (scores["retry"], 15),
            (scores["fallback"], 15),
        ]
    )


def test_reliability_summary_contains_recommendations(
    reliability_environment,
):
    experiment_service = reliability_environment[
        "experiment_service"
    ]
    service = reliability_environment["reliability_service"]

    experiment = create_reliability_experiment(
        experiment_service
    )

    experiment_service.run_experiment(experiment.experiment_id)

    summary = service.generate_reliability_summary()

    assert isinstance(summary["issues"], list)
    assert isinstance(summary["recommendations"], list)
    assert len(summary["recommendations"]) >= 1


def test_reliability_summary_is_tenant_isolated(
    reliability_environment,
):
    session = reliability_environment["session"]

    own_experiment_service = reliability_environment[
        "experiment_service"
    ]
    own_reliability_service = reliability_environment[
        "reliability_service"
    ]

    other_tenant = TenantRepository().create(
        session,
        f"Other Reliability Tenant {uuid.uuid4()}",
    )

    other_experiment_service = ExperimentService(
        session=session,
        tenant_id=str(other_tenant.tenant_id),
    )

    other_reliability_service = ExecutionReliabilityService(
        session=session,
        tenant_id=str(other_tenant.tenant_id),
    )

    own_experiment = create_reliability_experiment(
        own_experiment_service,
        "Own Tenant Experiment",
    )

    other_experiment = create_reliability_experiment(
        other_experiment_service,
        "Other Tenant Experiment",
    )

    own_experiment_service.run_experiment(
        own_experiment.experiment_id
    )

    other_experiment_service.run_experiment(
        other_experiment.experiment_id
    )

    own_summary = (
        own_reliability_service.generate_reliability_summary()
    )

    other_summary = (
        other_reliability_service.generate_reliability_summary()
    )

    assert own_summary["total_runs"] == 1
    assert other_summary["total_runs"] == 1

    session.delete(other_tenant)
    session.commit()


def test_high_retry_usage_generates_issue(
    reliability_environment,
):
    experiment_service = reliability_environment[
        "experiment_service"
    ]
    service = reliability_environment["reliability_service"]

    experiment = experiment_service.create_experiment(
        name="High Retry Experiment",
        scenarios=[
            FailureScenario(
                name="Retry scenario",
                failure_sequence=[
                    "timeout",
                    "timeout",
                    "none",
                ],
            )
        ],
        reliability_config=ReliabilityConfig(
            max_attempts=3,
            retry_strategy="fixed",
            base_delay=0,
            max_delay=0,
            jitter=False,
        ),
    )

    execution = experiment_service.run_experiment(
        experiment.experiment_id
    )

    summary = service.generate_reliability_summary()

    assert execution.total_retries == 2
    assert summary["average_retries"] == 2.0
    assert "High retry usage" in summary["issues"]


def test_high_latency_generates_issue(
    reliability_environment,
):
    experiment_service = reliability_environment[
        "experiment_service"
    ]

    from agentfault.services.execution_reliability_service import (
        ExecutionReliabilityService,
    )

    experiment = create_reliability_experiment(
        experiment_service,
        name="Latency Test Experiment",
    )

    experiment_service.run_experiment(
        experiment.experiment_id
    )

    service = ExecutionReliabilityService(
        session=reliability_environment["session"],
        tenant_id=str(
            reliability_environment["tenant"].tenant_id
        ),
        target_latency_ms=0.000001,
    )

    summary = service.generate_reliability_summary()

    assert summary["average_latency_ms"] > 0.000001
    assert "High average execution latency" in summary["issues"]


def test_successful_fallback_is_recorded_in_reliability_summary(
    reliability_environment,
):
    experiment_service = reliability_environment[
        "experiment_service"
    ]
    service = reliability_environment["reliability_service"]
    session = reliability_environment["session"]

    experiment = experiment_service.create_experiment(
        name="Successful Fallback Experiment",
        scenarios=[
            FailureScenario(
                name="Fallback scenario",
                failure_sequence=[
                    "timeout",
                    "timeout",
                    "timeout",
                ],
            )
        ],
        reliability_config=ReliabilityConfig(
            max_attempts=3,
            retry_strategy="fixed",
            base_delay=0,
            max_delay=0,
            jitter=False,
            enable_fallback=True,
        ),
    )

    execution = execute_experiment(
        experiment,
        fallback_tools=[
            lambda: simulated_tool("none")
        ],
    )

    experiment_service.execution_repository.save(
        session,
        execution,
        str(reliability_environment["tenant"].tenant_id),
    )

    summary = service.generate_reliability_summary()

    assert execution.scenario_results[0].fallback_count == 1
    assert execution.scenario_results[0].fallback_used is True
    assert summary["fallback_usage_rate"] == 1.0
    assert "High fallback usage" in summary["issues"]


def test_failed_fallback_attempt_is_not_counted_as_fallback_usage(
    reliability_environment,
):
    experiment_service = reliability_environment[
        "experiment_service"
    ]
    service = reliability_environment["reliability_service"]
    session = reliability_environment["session"]

    experiment = experiment_service.create_experiment(
        name="Failed Fallback Experiment",
        scenarios=[
            FailureScenario(
                name="Failed fallback scenario",
                failure_sequence=[
                    "timeout",
                    "timeout",
                    "timeout",
                ],
            )
        ],
        reliability_config=ReliabilityConfig(
            max_attempts=3,
            retry_strategy="fixed",
            base_delay=0,
            max_delay=0,
            jitter=False,
            enable_fallback=True,
        ),
    )

    execution = execute_experiment(
        experiment,
        fallback_tools=[
            lambda: simulated_tool("permission_denied")
        ],
    )

    experiment_service.execution_repository.save(
        session,
        execution,
        str(reliability_environment["tenant"].tenant_id),
    )

    summary = service.generate_reliability_summary()

    assert execution.scenario_results[0].fallback_count == 1
    assert execution.scenario_results[0].fallback_used is False
    assert summary["fallback_usage_rate"] == 0.0
