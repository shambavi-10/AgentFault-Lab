import time
from collections.abc import Callable

from agentfault.backoff import calculate_backoff
from agentfault.models import ToolResult
from agentfault.safe_execution import safe_tool_call
from agentfault.tracing import ExecutionTrace


def run_with_retry(
    tool_call: Callable[[], ToolResult],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    sleep_fn: Callable[[float], None] = time.sleep,
    trace: ExecutionTrace | None = None
) -> ToolResult:

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if base_delay < 0 or max_delay < 0:
        raise ValueError("Retry delays cannot be negative")

    if trace:
        trace.record("execution_started")

    for attempt in range(1, max_attempts + 1):

        start_time = time.perf_counter()

        if trace:
            trace.record(
                "tool_call_started",
                attempt=attempt
            )

        result = safe_tool_call(tool_call)

        duration_ms = (
            time.perf_counter() - start_time
        ) * 1000

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

        if not result.retryable:

            if trace:
                trace.record(
                    "execution_completed",
                    attempt=attempt,
                    status="failure"
                )

            return result

        if attempt == max_attempts:

            if trace:
                trace.record(
                    "execution_completed",
                    attempt=attempt,
                    status="failure"
                )

            return result

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