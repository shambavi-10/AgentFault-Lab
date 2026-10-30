
import time
from collections.abc import Callable

from agentfault.backoff import calculate_backoff
from agentfault.models import ToolResult


def run_with_retry(
    tool_call: Callable[[], ToolResult],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    sleep_fn: Callable[[float], None] = time.sleep
) -> ToolResult:
    """Execute a tool using bounded retries and exponential backoff."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if base_delay < 0 or max_delay < 0:
        raise ValueError("Retry delays cannot be negative")

    for attempt in range(1, max_attempts + 1):

        result = tool_call()

        if result.status == "success":
            return result

        if not result.retryable:
            return result

        if attempt == max_attempts:
            return result

        delay = calculate_backoff(
            attempt=attempt,
            base_delay=base_delay,
            max_delay=max_delay,
            jitter=jitter
        )

        sleep_fn(delay)

    raise RuntimeError("Unexpected retry state")
