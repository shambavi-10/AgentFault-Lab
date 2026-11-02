from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class TraceEvent:
    """Represents one event during tool execution."""

    event_type: str
    execution_id: str
    attempt: int = 0
    status: str | None = None
    error_type: str | None = None
    message: str | None = None
    duration_ms: float | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the event into a dictionary."""
        return {
            "event_type": self.event_type,
            "execution_id": self.execution_id,
            "attempt": self.attempt,
            "status": self.status,
            "error_type": self.error_type,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionTrace:
    """Stores all events belonging to one execution."""

    execution_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    events: list[TraceEvent] = field(default_factory=list)

    def record(
        self,
        event_type: str,
        attempt: int = 0,
        status: str | None = None,
        error_type: str | None = None,
        message: str | None = None,
        duration_ms: float | None = None,
    ) -> TraceEvent:
        """Record a new event in the execution trace."""

        event = TraceEvent(
            event_type=event_type,
            execution_id=self.execution_id,
            attempt=attempt,
            status=status,
            error_type=error_type,
            message=message,
            duration_ms=duration_ms,
        )

        self.events.append(event)

        return event

    def get_events(self) -> list[dict[str, Any]]:
        """Return all recorded events as dictionaries."""

        return [
            event.to_dict()
            for event in self.events
        ]

    def count_events(self, event_type: str) -> int:
        """Count events of a particular type."""

        return sum(
            1
            for event in self.events
            if event.event_type == event_type
        )