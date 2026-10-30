from agentfault.faults import simulated_tool, should_retry


def test_timeout_is_retryable():
    result = simulated_tool("timeout")
    assert should_retry(result) is True


def test_rate_limit_is_retryable():
    result = simulated_tool("rate_limit")
    assert should_retry(result) is True


def test_service_unavailable_is_retryable():
    result = simulated_tool("service_unavailable")
    assert should_retry(result) is True


def test_permission_denied_is_not_retryable():
    result = simulated_tool("permission_denied")
    assert should_retry(result) is False


def test_success_is_not_retryable():
    result = simulated_tool("none")
    assert should_retry(result) is False