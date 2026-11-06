
from math import isfinite
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from agentfault.database.repositories.execution_repository import (
    ExecutionRepository,
)


class ExecutionReliabilityService:
    """Generate reliability scores and insights from execution history."""

    def __init__(
        self,
        session: Session,
        tenant_id: str,
        execution_repository: ExecutionRepository | None = None,
        target_latency_ms: float = 1000.0,
        max_average_retries: float = 1.0,
        max_fallback_usage_rate: float = 0.2,
    ):
        if target_latency_ms <= 0:
            raise ValueError(
                "Target latency must be greater than zero"
            )

        if max_average_retries <= 0:
            raise ValueError(
                "Maximum average retries must be greater than zero"
            )

        if not 0 < max_fallback_usage_rate <= 1:
            raise ValueError(
                "Maximum fallback usage rate must be between 0 and 1"
            )

        self.session = session
        self.tenant_id = tenant_id
        self.execution_repository = (
            execution_repository or ExecutionRepository()
        )

        self.target_latency_ms = target_latency_ms
        self.max_average_retries = max_average_retries
        self.max_fallback_usage_rate = max_fallback_usage_rate

    @staticmethod
    def _calculate_efficiency_score(
        actual: float,
        threshold: float,
        weight: float,
    ) -> float:
        """Calculate a score that decreases above a threshold."""

        if actual <= threshold:
            return weight

        return round(
            max(0.0, weight * (2 - actual / threshold)),
            2,
        )

    def generate_reliability_summary(self) -> dict[str, Any]:
        """Generate an overall reliability summary for the tenant."""

        runs = self.execution_repository.list_by_tenant(
            self.session,
            self.tenant_id,
        )

        if not runs:
            return {
                "total_runs": 0,
                "total_scenarios": 0,
                "reliability_score": 0.0,
                "risk_level": "unknown",
                "success_rate": 0.0,
                "average_latency_ms": 0.0,
                "average_retries": 0.0,
                "fallback_usage_rate": 0.0,
                "circuit_breaker_enabled_scenarios": 0,
                "circuit_breaker_usage_rate": 0.0,
                "metric_scores": {
                    "success": 0.0,
                    "latency": 0.0,
                    "retry": 0.0,
                    "fallback": 0.0,
                },
                "issues": [
                    "No execution history available"
                ],
                "recommendations": [
                    "Run experiments to generate execution history."
                ],
            }

        total_runs = len(runs)

        total_scenarios = sum(
            len(run.scenario_results)
            for run in runs
        )

        all_scenarios = [
            scenario
            for run in runs
            for scenario in run.scenario_results
        ]

        success_rate = (
            sum(run.success_rate for run in runs) / total_runs
        )

        average_latency = mean(
            run.total_execution_time_ms
            for run in runs
        )

        average_retries = (
            sum(scenario.retry_count for scenario in all_scenarios)
            / total_scenarios
            if total_scenarios else 0.0
        )

        fallback_scenarios = sum(
            scenario.fallback_used
            for scenario in all_scenarios
        )

        fallback_usage_rate = (
            fallback_scenarios / total_scenarios
            if total_scenarios else 0.0
        )

        circuit_breaker_enabled = sum(
            scenario.circuit_breaker_enabled
            for scenario in all_scenarios
        )

        circuit_breaker_usage_rate = (
            circuit_breaker_enabled / total_scenarios
            if total_scenarios else 0.0
        )

        metrics = [
            success_rate,
            average_latency,
            average_retries,
            fallback_usage_rate,
            circuit_breaker_usage_rate,
        ]

        if any(not isfinite(value) for value in metrics):
            raise ValueError(
                "Execution history contains non-finite metrics"
            )

        if not 0 <= success_rate <= 1:
            raise ValueError("Invalid success rate in execution history")

        if (
            average_latency < 0
            or average_retries < 0
            or not 0 <= fallback_usage_rate <= 1
        ):
            raise ValueError("Invalid execution metrics")

        success_score = round(success_rate * 50, 2)

        latency_score = round(
            max(
                0.0,
                20 * (
                    1 - average_latency / self.target_latency_ms
                ),
            ),
            2,
        )

        retry_score = self._calculate_efficiency_score(
            average_retries,
            self.max_average_retries,
            15,
        )

        fallback_score = self._calculate_efficiency_score(
            fallback_usage_rate,
            self.max_fallback_usage_rate,
            15,
        )

        reliability_score = round(
            success_score
            + latency_score
            + retry_score
            + fallback_score,
            2,
        )

        if reliability_score >= 80:
            risk_level = "low"
        elif reliability_score >= 60:
            risk_level = "medium"
        else:
            risk_level = "high"

        issues = []
        recommendations = []

        if success_rate < 0.8:
            issues.append("Low scenario success rate")
            recommendations.append(
                "Investigate failed scenarios and recurring failure causes."
            )

        if average_latency > self.target_latency_ms:
            issues.append("High average execution latency")
            recommendations.append(
                "Investigate slow tools, network delays, and unnecessary processing."
            )

        if average_retries > self.max_average_retries:
            issues.append("High retry usage")
            recommendations.append(
                "Review retry policies and frequently failing operations."
            )

        if fallback_usage_rate > self.max_fallback_usage_rate:
            issues.append("High fallback usage")
            recommendations.append(
                "Investigate primary tool failures and improve primary execution reliability."
            )

        if not issues:
            recommendations.append(
                "Reliability is within configured thresholds. Continue monitoring."
            )

        return {
            "total_runs": total_runs,
            "total_scenarios": total_scenarios,
            "reliability_score": reliability_score,
            "risk_level": risk_level,
            "success_rate": round(success_rate, 4),
            "average_latency_ms": round(average_latency, 4),
            "average_retries": round(average_retries, 4),
            "fallback_usage_rate": round(
                fallback_usage_rate, 4
            ),
            "circuit_breaker_enabled_scenarios": (
                circuit_breaker_enabled
            ),
            "circuit_breaker_usage_rate": round(
                circuit_breaker_usage_rate, 4
            ),
            "metric_scores": {
                "success": success_score,
                "latency": latency_score,
                "retry": retry_score,
                "fallback": fallback_score,
            },
            "issues": issues,
            "recommendations": recommendations,
        }
