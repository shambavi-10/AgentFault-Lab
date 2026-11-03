
from collections.abc import Callable, Sequence

from agentfault.models import ToolResult
from agentfault.safe_execution import safe_tool_call
from agentfault.tracing import ExecutionTrace


def execute_with_fallback(
    primary_tool: Callable[[], ToolResult],
    fallback_tool: Callable[[], ToolResult] | None = None,
    trace: ExecutionTrace | None = None,
    fallback_tools: Sequence[Callable[[], ToolResult]] | None = None,
) -> ToolResult:
    """Execute a primary tool and try fallback tools after retryable failures.

    Supports both the original single-fallback argument and a fallback chain.
    """

    if fallback_tool is not None and fallback_tools is not None:
        raise ValueError(
            "Provide fallback_tool or fallback_tools, not both"
        )

    tools = []

    if fallback_tools is not None:
        tools.extend(fallback_tools)
    elif fallback_tool is not None:
        tools.append(fallback_tool)

    if trace:
        trace.record("fallback_execution_started")

    # Execute the primary tool.
    if trace:
        trace.record("primary_tool_started")

    result = safe_tool_call(primary_tool)

    if result.status == "success":
        if trace:
            trace.record(
                "primary_tool_succeeded",
                status="success"
            )
            trace.record(
                "fallback_execution_completed",
                status="success",
                message="Primary tool succeeded. Fallback was not needed."
            )

        return result

    if trace:
        trace.record(
            "primary_tool_failed",
            status="failure",
            error_type=result.error_type,
            message=result.error
        )

    # Stop if the primary failure is not retryable.
    if not result.retryable:
        if trace:
            trace.record(
                "fallback_skipped",
                status="failure",
                message="Primary failure is not retryable."
            )
            trace.record(
                "fallback_execution_completed",
                status="failure"
            )

        return result

    # Try each fallback tool in order.
    for index, fallback in enumerate(tools, start=1):

        if trace:
            trace.record(
                "fallback_tool_started",
                attempt=index,
                message=f"Starting fallback tool {index}"
            )

        fallback_result = safe_tool_call(fallback)

        if fallback_result.status == "success":
            if trace:
                trace.record(
                    "fallback_tool_succeeded",
                    attempt=index,
                    status="success",
                    message=f"Fallback tool {index} succeeded."
                )
                trace.record(
                    "fallback_execution_completed",
                    status="success"
                )

            return fallback_result

        if trace:
            trace.record(
                "fallback_tool_failed",
                attempt=index,
                status="failure",
                error_type=fallback_result.error_type,
                message=fallback_result.error
            )

        # Stop when a fallback returns a permanent failure.
        if not fallback_result.retryable:
            if trace:
                trace.record(
                    "fallback_execution_completed",
                    status="failure",
                    message="Fallback returned a non-retryable failure."
                )

            return fallback_result

        # Continue to the next fallback after retryable failure.
        result = fallback_result

    if trace:
        trace.record(
            "fallback_execution_completed",
            status="failure",
            message="All available tools failed."
        )

    return result
