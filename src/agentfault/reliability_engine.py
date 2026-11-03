
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from time import perf_counter

from agentfault.circuit_breaker import CircuitBreaker
from agentfault.models import ToolResult
from agentfault.reliability_config import ReliabilityConfig
from agentfault.retry import run_with_retry
from agentfault.safe_execution import safe_tool_call
from agentfault.tracing import ExecutionTrace


@dataclass
class ReliabilityExecution:
    """Result and metrics from a unified reliability execution."""

    result: ToolResult
    trace: ExecutionTrace
    execution_time_ms: float
    retry_count: int
    fallback_count: int
    scheduled_backoff_seconds: float
    fallback_used: bool
    circuit_breaker_enabled: bool


@dataclass
class ReliabilityEngine:
    """Coordinates retry, circuit breaker and fallback strategies."""

    config: ReliabilityConfig
    trace: ExecutionTrace = field(default_factory=ExecutionTrace)

    def execute(
        self,
        primary_tool: Callable[[], ToolResult],
        fallback_tools: Sequence[Callable[[], ToolResult]] | None = None,
        sleep_fn: Callable[[float], None] = lambda delay: None,
    ) -> ReliabilityExecution:

        if fallback_tools is not None and not self.config.enable_fallback:
            raise ValueError(
                "Fallback tools supplied while fallback is disabled"
            )
        self.trace = ExecutionTrace()

        scheduled_delays: list[float] = []
        fallback_count = 0
        fallback_used = False

        circuit_breaker = None

        if self.config.enable_circuit_breaker:
            circuit_breaker = CircuitBreaker(
                failure_threshold=self.config.failure_threshold,
                recovery_timeout=self.config.recovery_timeout,
                trace=self.trace,
            )

        start_time = perf_counter()

        self.trace.record("reliability_execution_started")

        def record_delay(delay: float) -> None:
            scheduled_delays.append(delay)
            sleep_fn(delay)

        result = run_with_retry(
            tool_call=primary_tool,
            max_attempts=self.config.max_attempts,
            retry_strategy=self.config.retry_strategy,
            base_delay=self.config.base_delay,
            max_delay=self.config.max_delay,
            jitter=self.config.jitter,
            sleep_fn=record_delay,
            trace=self.trace,
            circuit_breaker=circuit_breaker,
        )

        if result.status == "failure" and self.config.enable_fallback:
            if result.retryable or result.error_type == "circuit_open":

                for index, fallback_tool in enumerate(
                    fallback_tools or [], start=1
                ):
                    fallback_count += 1

                    self.trace.record(
                        "unified_fallback_started",
                        attempt=index,
                        message=f"Starting fallback tool {index}",
                    )

                    fallback_result = safe_tool_call(fallback_tool)

                    if fallback_result.status == "success":
                        result = fallback_result
                        fallback_used = True

                        self.trace.record(
                            "unified_fallback_succeeded",
                            attempt=index,
                            status="success",
                        )
                        break

                    self.trace.record(
                        "unified_fallback_failed",
                        attempt=index,
                        status="failure",
                        error_type=fallback_result.error_type,
                        message=fallback_result.error,
                    )

                    result = fallback_result

                    if not fallback_result.retryable:
                        break

        execution_time_ms = (perf_counter() - start_time) * 1000

        retry_count = self.trace.count_events("retry_scheduled")

        self.trace.record(
            "reliability_execution_completed",
            status=result.status,
            message="Unified reliability execution completed.",
        )

        return ReliabilityExecution(
            result=result,
            trace=self.trace,
            execution_time_ms=execution_time_ms,
            retry_count=retry_count,
            fallback_count=fallback_count,
            scheduled_backoff_seconds=sum(scheduled_delays),
            fallback_used=fallback_used,
            circuit_breaker_enabled=self.config.enable_circuit_breaker,
        )
