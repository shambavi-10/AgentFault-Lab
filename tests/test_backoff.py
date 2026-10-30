import pytest

from agentfault.backoff import calculate_backoff


def test_exponential_growth():
    assert calculate_backoff(1, jitter=False) == 1
    assert calculate_backoff(2, jitter=False) == 2
    assert calculate_backoff(3, jitter=False) == 4


def test_maximum_delay():
    delay = calculate_backoff(
        attempt=10,
        base_delay=1,
        max_delay=8,
        jitter=False
    )

    assert delay == 8


def test_jitter_range():
    delay = calculate_backoff(
        attempt=3,
        base_delay=1,
        jitter=True
    )

    assert 0 <= delay <= 4


def test_invalid_attempt():
    with pytest.raises(ValueError):
        calculate_backoff(0)


def test_negative_delay():
    with pytest.raises(ValueError):
        calculate_backoff(1, base_delay=-1)


def test_negative_max_delay():
    with pytest.raises(ValueError):
        calculate_backoff(1, max_delay=-1)