from agentfault.metrics import calculate_reliability_metrics


def test_calculate_success_and_failure_rates():

    traces = [
        [
            {
                "event_type": "execution_completed",
                "status": "success"
            }
        ],
        [
            {
                "event_type": "execution_completed",
                "status": "success"
            }
        ],
        [
            {
                "event_type": "execution_completed",
                "status": "failure"
            }
        ]
    ]

    metrics = calculate_reliability_metrics(traces)

    assert metrics["total_executions"] == 3
    assert metrics["successful_executions"] == 2
    assert metrics["failed_executions"] == 1
    assert metrics["success_rate"] == 66.67
    assert metrics["failure_rate"] == 33.33


def test_calculate_total_retries():

    traces = [
        [
            {"event_type": "retry_scheduled"},
            {"event_type": "retry_scheduled"},
            {"event_type": "execution_completed", "status": "success"}
        ],
        [
            {"event_type": "retry_scheduled"},
            {"event_type": "execution_completed", "status": "failure"}
        ]
    ]

    metrics = calculate_reliability_metrics(traces)

    assert metrics["total_retries"] == 3


def test_calculate_average_latency():

    traces = [
        [
            {
                "event_type": "tool_call_succeeded",
                "duration_ms": 100
            },
            {
                "event_type": "tool_call_failed",
                "duration_ms": 200
            }
        ]
    ]

    metrics = calculate_reliability_metrics(traces)

    assert metrics["average_latency_ms"] == 150


def test_empty_traces():

    metrics = calculate_reliability_metrics([])

    assert metrics["total_executions"] == 0
    assert metrics["success_rate"] == 0
    assert metrics["failure_rate"] == 0
    assert metrics["total_retries"] == 0
    assert metrics["average_latency_ms"] == 0


def test_all_executions_successful():

    traces = [
        [
            {
                "event_type": "execution_completed",
                "status": "success"
            }
        ],
        [
            {
                "event_type": "execution_completed",
                "status": "success"
            }
        ]
    ]

    metrics = calculate_reliability_metrics(traces)

    assert metrics["success_rate"] == 100
    assert metrics["failure_rate"] == 0