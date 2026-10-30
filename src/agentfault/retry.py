from collections.abc import Callable

from agentfault.models import ToolResult


def run_with_retry(
    tool_call: Callable[[], ToolResult],
    max_attempts: int = 3
) -> ToolResult:
    """
    Execute a tool with retry support.

    Retry only when the failure is retryable.
    Stop after reaching the maximum attempts.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    last_result = None

    for attempt in range(1, max_attempts + 1):
        result = tool_call()
        print(f"Attempt {attempt}: {result.status}")

        if result.status == "success":
            return result

        if not result.retryable:
            return result

        last_result = result

    return last_result