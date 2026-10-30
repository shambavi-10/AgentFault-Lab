
import pytest
from pydantic import ValidationError

from agentfault.models import ToolResult


def test_valid_success_result():
    result = ToolResult(
        status="success",
        data={"amount": 100}
    )

    assert result.status == "success"
    assert result.data == {"amount": 100}


def test_valid_failure_result():
    result = ToolResult(
        status="failure",
        error="The tool timed out",
        error_type="timeout"
    )

    assert result.status == "failure"
    assert result.error_type == "timeout"


def test_success_requires_data():
    with pytest.raises(ValidationError):
        ToolResult(status="success")


def test_success_cannot_contain_error():
    with pytest.raises(ValidationError):
        ToolResult(
            status="success",
            data={"amount": 100},
            error="Unexpected error"
        )


def test_failure_requires_error():
    with pytest.raises(ValidationError):
        ToolResult(status="failure")


def test_failure_cannot_contain_data():
    with pytest.raises(ValidationError):
        ToolResult(
            status="failure",
            data={"amount": 100},
            error="Operation failed"
        )


def test_invalid_status_is_rejected():
    with pytest.raises(ValidationError):
        ToolResult(status="pending")
