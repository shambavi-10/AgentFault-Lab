from collections.abc import Callable

from agentfault.circuit_breaker import CircuitBreaker
from agentfault.models import ToolResult


def safe_tool_call(
    tool_call: Callable[[], ToolResult]
) -> ToolResult:
    """Execute a tool safely and convert exceptions into ToolResult."""

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


def execute_with_permission(
    tool_call: Callable[[], ToolResult],
    circuit_breaker: CircuitBreaker,
    is_probe: bool
) -> ToolResult:
    """Execute a tool after circuit-breaker permission is acquired."""

    result = safe_tool_call(tool_call)

    if result.status == "success":
        circuit_breaker.record_success(is_probe=is_probe)
    else:
        circuit_breaker.record_failure(is_probe=is_probe)

    return result


def safe_tool_call_with_circuit_breaker(
    tool_call: Callable[[], ToolResult],
    circuit_breaker: CircuitBreaker
) -> ToolResult:
    """Execute a tool through a circuit breaker."""

    allowed, is_probe = circuit_breaker.acquire_permission()

    if not allowed:
        return ToolResult(
            status="failure",
            error="Circuit breaker is OPEN. Tool execution blocked.",
            error_type="circuit_open",
            retryable=False
        )

    return execute_with_permission(
        tool_call,
        circuit_breaker,
        is_probe
    )
