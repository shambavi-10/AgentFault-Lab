
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentfault.database.base import Base


class ExperimentRunModel(Base):
    """Persistent record of one experiment execution."""

    __tablename__ = "experiment_runs"

    __table_args__ = (
        Index("ix_experiment_runs_experiment_id", "experiment_id"),
        Index("ix_experiment_runs_status", "status"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.experiment_id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False)
    total_scenarios: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_scenarios: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_scenarios: Mapped[int] = mapped_column(Integer, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    total_retries: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    experiment: Mapped["ExperimentModel"] = relationship(
        back_populates="runs",
    )

    scenario_results: Mapped[list["ScenarioExecutionResultModel"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ScenarioExecutionResultModel.position",
    )
