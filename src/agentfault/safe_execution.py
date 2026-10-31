from collections.abc import Callable

from agentfault.models import ToolResult


def safe_tool_call(
    tool_call: Callable[[], ToolResult]
) -> ToolResult:
    """
    Execute a tool safely.

    Convert unexpected exceptions into structured ToolResult failures.
    """

    try:
        result = tool_call()

        if not isinstance(result, ToolResult):
            return ToolResult(
                status="failure",
                error="Tool returned an invalid response type",
                error_type="invalid_response",
                retryable=False
            )

        return result

    except TimeoutError as error:
        return ToolResult(
            status="failure",
            error=str(error),
            error_type="timeout",
            retryable=True
        )

    except ConnectionError as error:
        return ToolResult(
            status="failure",
            error=str(error),
            error_type="connection_error",
            retryable=True
        )

    except Exception as error:
        return ToolResult(
            status="failure",
            error=str(error),
            error_type=type(error).__name__,
            retryable=False
        )