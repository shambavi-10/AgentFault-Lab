
import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentfault.database.base import Base


class ExperimentScenarioModel(Base):
    """Persistent database representation of an experiment scenario."""

    __tablename__ = "experiment_scenarios"

    __table_args__ = (
        CheckConstraint(
            "expected_status IN ('success', 'failure')",
            name="ck_experiment_scenarios_expected_status",
        ),
        Index("ix_experiment_scenarios_experiment_id", "experiment_id"),
    )

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.experiment_id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    failure_sequence: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )

    expected_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    experiment: Mapped["ExperimentModel"] = relationship(
        back_populates="scenarios",
    )
