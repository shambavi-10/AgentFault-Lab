
import time
from enum import Enum
from threading import Lock

from agentfault.tracing import ExecutionTrace


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Controls access to an unreliable external service."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 10.0,
        trace: ExecutionTrace | None = None
    ):
        if failure_threshold < 1:
            raise ValueError("Failure threshold must be at least 1")

        if recovery_timeout < 0:
            raise ValueError("Recovery timeout cannot be negative")

        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.trace = trace

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

        self._lock = Lock()
        self._probe_in_progress = False

    def _record_transition(self, event_type: str, message: str):
        """Record a circuit-breaker event when tracing is enabled."""

        if self.trace is not None:
            self.trace.record(
                event_type,
                message=message
            )

    def acquire_permission(self) -> tuple[bool, bool]:
        """Atomically check permission and identify recovery probes."""

        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True, False

            if self.state == CircuitState.OPEN:
                elapsed = time.monotonic() - self.last_failure_time

                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self._probe_in_progress = True

                    self._record_transition(
                        "circuit_breaker_half_open",
                        "Recovery timeout elapsed. Recovery probe allowed."
                    )

                    return True, True

                return False, False

            if self.state == CircuitState.HALF_OPEN:
                if not self._probe_in_progress:
                    self._probe_in_progress = True
                    return True, True

                return False, False

            return False, False

    def allow_request(self) -> bool:
        """Allow normal requests or reserve one recovery probe."""

        allowed, _ = self.acquire_permission()
        return allowed

    def record_success(self, is_probe: bool = False):
        """Record success without allowing unrelated calls to close the circuit."""

        with self._lock:
            if self.state == CircuitState.HALF_OPEN and not is_probe:
                return

            if self.state == CircuitState.HALF_OPEN and is_probe:
                self.failure_count = 0
                self.last_failure_time = None
                self._probe_in_progress = False
                self.state = CircuitState.CLOSED

                self._record_transition(
                    "circuit_breaker_closed",
                    "Recovery probe succeeded. Circuit closed."
                )
                return

            if self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self, is_probe: bool = False):
        """Record failure and update circuit state."""

        with self._lock:
            if self.state == CircuitState.HALF_OPEN and not is_probe:
                return

            if self.state == CircuitState.OPEN:
                return

            self.failure_count += 1
            self.last_failure_time = time.monotonic()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self._probe_in_progress = False

                self._record_transition(
                    "circuit_breaker_opened",
                    "Recovery probe failed. Circuit reopened."
                )
                return

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

                self._record_transition(
                    "circuit_breaker_opened",
                    "Failure threshold reached. Circuit opened."
                )
