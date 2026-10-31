import pytest

from agentfault.models import ToolResult
from agentfault.safe_execution import safe_tool_call


def test_successful_tool_call():
    def fake_tool():
        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = safe_tool_call(fake_tool)

    assert result.status == "success"
    assert result.data == {"amount": 100}


def test_timeout_exception():
    def fake_tool():
        raise TimeoutError("Request timed out")

    result = safe_tool_call(fake_tool)

    assert result.status == "failure"
    assert result.error == "Request timed out"
    assert result.error_type == "timeout"
    assert result.retryable is True


def test_connection_error():
    def fake_tool():
        raise ConnectionError("Connection lost")

    result = safe_tool_call(fake_tool)

    assert result.status == "failure"
    assert result.error == "Connection lost"
    assert result.error_type == "connection_error"
    assert result.retryable is True


def test_unexpected_exception():
    def fake_tool():
        raise ValueError("Invalid input")

    result = safe_tool_call(fake_tool)

    assert result.status == "failure"
    assert result.error == "Invalid input"
    assert result.error_type == "ValueError"
    assert result.retryable is False


def test_invalid_response_type():
    def fake_tool():
        return "Invalid response"

    result = safe_tool_call(fake_tool)

    assert result.status == "failure"
    assert result.error_type == "invalid_response"
    assert result.retryable is False