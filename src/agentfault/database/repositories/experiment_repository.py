
import uuid
from dataclasses import asdict
from typing import Union

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from agentfault.database.models.experiment import ExperimentModel
from agentfault.database.models.experiment_scenario import (
    ExperimentScenarioModel,
)
from agentfault.experiment import Experiment
from agentfault.reliability_config import ReliabilityConfig
from agentfault.scenarios import FailureScenario


class ExperimentRepository:
    """Handles tenant-scoped experiment persistence in PostgreSQL."""

    @staticmethod
    def _to_uuid(value: Union[str, uuid.UUID]) -> uuid.UUID:
        """Convert a string or UUID into a UUID object."""
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"Invalid UUID: {value}") from exc

    @staticmethod
    def _to_domain(model: ExperimentModel) -> Experiment:
        """Convert a database model into the original domain object."""

        scenarios = [
            FailureScenario(
                name=scenario.name,
                failure_sequence=list(scenario.failure_sequence),
                expected_status=scenario.expected_status,
            )
            for scenario in model.scenarios
        ]

        reliability_config = ReliabilityConfig(
            **model.reliability_config
        )

        return Experiment(
            name=model.name,
            scenarios=scenarios,
            description=model.description,
            reliability_config=reliability_config,
            experiment_id=str(model.experiment_id),
            status=model.status,
            created_at=model.created_at,
        )

    def create(
        self,
        session: Session,
        experiment: Experiment,
        tenant_id: Union[str, uuid.UUID],
    ) -> Experiment:
        """Persist a new experiment and its scenarios."""

        if not isinstance(experiment, Experiment):
            raise TypeError("Expected an Experiment instance")

        tenant_uuid = self._to_uuid(tenant_id)
        experiment_uuid = self._to_uuid(experiment.experiment_id)

        existing = session.scalar(
            select(ExperimentModel).where(
                ExperimentModel.experiment_id == experiment_uuid
            )
        )

        if existing is not None:
            raise ValueError(
                f"Experiment already exists: {experiment.experiment_id}"
            )

        model = ExperimentModel(
            experiment_id=experiment_uuid,
            tenant_id=tenant_uuid,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status,
            reliability_config=asdict(experiment.reliability_config),
            created_at=experiment.created_at,
            scenarios=[
                ExperimentScenarioModel(
                    name=scenario.name,
                    failure_sequence=list(scenario.failure_sequence),
                    expected_status=scenario.expected_status,
                    position=position,
                )
                for position, scenario in enumerate(experiment.scenarios)
            ],
        )

        try:
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_domain(model)
        except Exception:
            session.rollback()
            raise

    def get_by_id(
        self,
        session: Session,
        experiment_id: Union[str, uuid.UUID],
        tenant_id: Union[str, uuid.UUID],
    ) -> Experiment | None:
        """Retrieve an experiment belonging to a specific tenant."""

        experiment_uuid = self._to_uuid(experiment_id)
        tenant_uuid = self._to_uuid(tenant_id)

        statement = (
            select(ExperimentModel)
            .options(selectinload(ExperimentModel.scenarios))
            .where(
                ExperimentModel.experiment_id == experiment_uuid,
                ExperimentModel.tenant_id == tenant_uuid,
            )
        )

        model = session.scalar(statement)

        if model is None:
            return None

        return self._to_domain(model)

    def list_by_tenant(
        self,
        session: Session,
        tenant_id: Union[str, uuid.UUID],
    ) -> list[Experiment]:
        """List experiments belonging only to the requested tenant."""

        tenant_uuid = self._to_uuid(tenant_id)

        statement = (
            select(ExperimentModel)
            .options(selectinload(ExperimentModel.scenarios))
            .where(ExperimentModel.tenant_id == tenant_uuid)
            .order_by(ExperimentModel.created_at.desc())
        )

        models = session.scalars(statement).all()

        return [
            self._to_domain(model)
            for model in models
        ]

    def update_status(
        self,
        session: Session,
        experiment_id: Union[str, uuid.UUID],
        tenant_id: Union[str, uuid.UUID],
        status: str,
    ) -> Experiment:
        """Update an experiment's status within its tenant."""

        experiment_uuid = self._to_uuid(experiment_id)
        tenant_uuid = self._to_uuid(tenant_id)

        statement = (
            select(ExperimentModel)
            .options(selectinload(ExperimentModel.scenarios))
            .where(
                ExperimentModel.experiment_id == experiment_uuid,
                ExperimentModel.tenant_id == tenant_uuid,
            )
        )

        model = session.scalar(statement)

        if model is None:
            raise KeyError(f"Experiment not found: {experiment_id}")

        if status not in {"pending", "running", "completed", "failed"}:
            raise ValueError("Invalid experiment status")

        model.status = status

        try:
            session.commit()
            session.refresh(model)
            return self._to_domain(model)
        except Exception:
            session.rollback()
            raise

    def delete_pending(
        self,
        session: Session,
        experiment_id: Union[str, uuid.UUID],
        tenant_id: Union[str, uuid.UUID],
    ) -> None:
        """Delete an experiment only when it is pending."""

        experiment_uuid = self._to_uuid(experiment_id)
        tenant_uuid = self._to_uuid(tenant_id)

        model = session.scalar(
            select(ExperimentModel).where(
                ExperimentModel.experiment_id == experiment_uuid,
                ExperimentModel.tenant_id == tenant_uuid,
            )
        )

        if model is None:
            raise KeyError(f"Experiment not found: {experiment_id}")

        if model.status != "pending":
            raise ValueError(
                "Only pending experiments can be deleted"
            )

        try:
            session.delete(model)
            session.commit()
        except Exception:
            session.rollback()
            raise
