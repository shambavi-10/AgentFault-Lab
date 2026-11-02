from statistics import mean
from typing import Any


def calculate_reliability_metrics(
    traces: list[list[dict[str, Any]]]
) -> dict[str, Any]:
    """
    Calculate reliability metrics from execution traces.
    """

    total_executions = len(traces)

    successful_executions = 0
    failed_executions = 0
    total_retries = 0
    durations = []

    for events in traces:

        for event in events:

            if event["event_type"] == "execution_completed":

                if event["status"] == "success":
                    successful_executions += 1

                elif event["status"] == "failure":
                    failed_executions += 1

            if event["event_type"] == "retry_scheduled":
                total_retries += 1

            if event["event_type"] in (
                "tool_call_succeeded",
                "tool_call_failed"
            ):
                duration = event.get("duration_ms")

                if duration is not None:
                    durations.append(duration)

    success_rate = (
        successful_executions / total_executions * 100
        if total_executions > 0 else 0
    )

    failure_rate = (
        failed_executions / total_executions * 100
        if total_executions > 0 else 0
    )

    average_latency = (
        mean(durations)
        if durations else 0
    )

    return {
        "total_executions": total_executions,
        "successful_executions": successful_executions,
        "failed_executions": failed_executions,
        "success_rate": round(success_rate, 2),
        "failure_rate": round(failure_rate, 2),
        "total_retries": total_retries,
        "average_latency_ms": round(average_latency, 2),
    }