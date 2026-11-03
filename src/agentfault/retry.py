
import time
from collections.abc import Callable
from typing import Literal

from agentfault.backoff import calculate_backoff
from agentfault.circuit_breaker import CircuitBreaker
from agentfault.models import ToolResult
from agentfault.safe_execution import (
    safe_tool_call,
    safe_tool_call_with_circuit_breaker
)
from agentfault.tracing import ExecutionTrace


def run_with_retry(
    tool_call: Callable[[], ToolResult],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    sleep_fn: Callable[[float], None] = time.sleep,
    trace: ExecutionTrace | None = None,
    retry_strategy: Literal[
        "none", "fixed", "exponential"
    ] = "exponential",
    circuit_breaker: CircuitBreaker | None = None
) -> ToolResult:

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if base_delay < 0 or max_delay < 0:
        raise ValueError("Retry delays cannot be negative")

    if retry_strategy not in {"none", "fixed", "exponential"}:
        raise ValueError("Unsupported retry strategy")

    if retry_strategy == "none":
        max_attempts = 1

    if trace:
        trace.record("execution_started")

    for attempt in range(1, max_attempts + 1):

        start_time = time.perf_counter()

        # Execute the tool through the circuit breaker.
        if circuit_breaker is not None:
            result = safe_tool_call_with_circuit_breaker(
                tool_call,
                circuit_breaker
            )
        else:
            result = safe_tool_call(tool_call)

        duration_ms = (
            time.perf_counter() - start_time
        ) * 1000

        # A blocked request is not an actual tool execution.
        if result.error_type == "circuit_open":

            if trace:
                trace.record(
                    "circuit_breaker_blocked",
                    attempt=attempt,
                    status="failure",
                    error_type="circuit_open",
                    message="Circuit breaker blocked tool execution",
                    duration_ms=duration_ms
                )

                trace.record(
                    "execution_completed",
                    attempt=attempt,
                    status="failure"
                )

            return result

        # Record actual tool execution.
        if trace:
            trace.record(
                "tool_call_started",
                attempt=attempt
            )

        if result.status == "success":

            if trace:
                trace.record(
                    "tool_call_succeeded",
                    attempt=attempt,
                    status="success",
                    duration_ms=duration_ms
                )

                trace.record(
                    "execution_completed",
                    attempt=attempt,
                    status="success"
                )

            return result

        if trace:
            trace.record(
                "tool_call_failed",
                attempt=attempt,
                status="failure",
                error_type=result.error_type,
                message=result.error,
                duration_ms=duration_ms
            )

        if not result.retryable or attempt == max_attempts:

            if trace:
                trace.record(
                    "execution_completed",
                    attempt=attempt,
                    status="failure"
                )

            return result

        if retry_strategy == "fixed":
            delay = min(base_delay, max_delay)

        else:
            delay = calculate_backoff(
                attempt=attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter
            )

        if trace:
            trace.record(
                "retry_scheduled",
                attempt=attempt,
                message=f"Retry scheduled after {delay:.2f} seconds"
            )

        sleep_fn(delay)

    raise RuntimeError("Unexpected retry state")
