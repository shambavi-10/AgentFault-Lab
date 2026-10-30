import random


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True
) -> float:
    """Calculate a bounded exponential retry delay."""

    if attempt < 1:
        raise ValueError("attempt must be at least 1")

    if base_delay < 0:
        raise ValueError("base_delay cannot be negative")

    if max_delay < 0:
        raise ValueError("max_delay cannot be negative")

    delay = min(
        max_delay,
        base_delay * (2 ** (attempt - 1))
    )

    if jitter:
        return random.uniform(0, delay)

    return delay