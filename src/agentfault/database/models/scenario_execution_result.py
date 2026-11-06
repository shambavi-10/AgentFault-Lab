import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentfault.database.base import Base


class ScenarioExecutionResultModel(Base):
    """Persistent result of an individual scenario execution."""

    __tablename__ = "scenario_execution_results"

    __table_args__ = (
        Index("ix_scenario_execution_results_run_id", "run_id"),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiment_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )

    scenario_name: Mapped[str] = mapped_column(String(200), nullable=False)
    expected_status: Mapped[str] = mapped_column(String(20), nullable=False)
    result_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fallback_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    circuit_breaker_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    valid_business_result: Mapped[bool] = mapped_column(Boolean, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    run: Mapped["ExperimentRunModel"] = relationship(
        back_populates="scenario_results",
    )
    trace_events: Mapped[list["ExecutionTraceEventModel"]] = relationship(
    back_populates="scenario_result",
    cascade="all, delete-orphan",
    order_by="ExecutionTraceEventModel.timestamp",
)