import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentfault.database.base import Base


class ExecutionTraceEventModel(Base):
    """Persistent record of an individual execution trace event."""

    __tablename__ = "execution_trace_events"

    __table_args__ = (
        Index("ix_execution_trace_events_result_id", "result_id"),
        Index("ix_execution_trace_events_execution_id", "execution_id"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "scenario_execution_results.result_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    execution_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    scenario_result: Mapped["ScenarioExecutionResultModel"] = relationship(
        back_populates="trace_events",
    )
