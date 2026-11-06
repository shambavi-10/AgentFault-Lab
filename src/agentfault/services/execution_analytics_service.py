
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from agentfault.database.repositories.execution_repository import (
    ExecutionRepository,
)


class ExecutionAnalyticsService:
    """Provides analytics from persisted experiment execution history."""

    def __init__(
        self,
        session: Session,
        tenant_id: str,
        execution_repository: ExecutionRepository | None = None,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.execution_repository = (
            execution_repository or ExecutionRepository()
        )

    def get_execution_overview(self) -> dict[str, Any]:
        """Return aggregate execution metrics for the current tenant."""

        runs = self.execution_repository.list_by_tenant(
            self.session,
            self.tenant_id,
        )

        total_runs = len(runs)

        completed_runs = sum(
            run.status == "completed" for run in runs
        )

        failed_runs = sum(
            run.status == "failed" for run in runs
        )

        total_scenarios = sum(
            run.total_scenarios for run in runs
        )

        total_retries = sum(
            run.total_retries for run in runs
        )

        average_success_rate = (
            mean(run.success_rate for run in runs)
            if runs else 0.0
        )

        average_execution_time_ms = (
            mean(run.total_execution_time_ms for run in runs)
            if runs else 0.0
        )

        return {
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "total_scenarios": total_scenarios,
            "average_success_rate": round(
                average_success_rate, 4
            ),
            "average_execution_time_ms": round(
                average_execution_time_ms, 4
            ),
            "total_retries": total_retries,
        }

    def get_success_rate_trend(self) -> list[dict[str, Any]]:
        """Return success-rate history for the current tenant."""

        runs = self.execution_repository.list_by_tenant(
            self.session,
            self.tenant_id,
        )

        ordered_runs = sorted(
            runs,
            key=lambda run: run.created_at,
        )

        return [
            {
                "run_id": str(run.run_id),
                "created_at": run.created_at.isoformat(),
                "success_rate": run.success_rate,
                "passed_scenarios": run.passed_scenarios,
                "failed_scenarios": run.failed_scenarios,
            }
            for run in ordered_runs
        ]

    def get_latency_trend(self) -> list[dict[str, Any]]:
        """Return execution latency history for the current tenant."""

        runs = self.execution_repository.list_by_tenant(
            self.session,
            self.tenant_id,
        )

        ordered_runs = sorted(
            runs,
            key=lambda run: run.created_at,
        )

        latency_data = []

        for run in ordered_runs:
            scenario_times = [
                scenario.execution_time_ms
                for scenario in run.scenario_results
            ]

            average_scenario_time = (
                mean(scenario_times)
                if scenario_times else 0.0
            )

            slowest_scenario_time = (
                max(scenario_times)
                if scenario_times else 0.0
            )

            slowest_scenario = (
                max(
                    run.scenario_results,
                    key=lambda scenario: scenario.execution_time_ms,
                )
                if run.scenario_results else None
            )

            latency_data.append({
                "run_id": str(run.run_id),
                "created_at": run.created_at.isoformat(),
                "total_execution_time_ms": (
                    run.total_execution_time_ms
                ),
                "average_scenario_time_ms": round(
                    average_scenario_time, 4
                ),
                "slowest_scenario_time_ms": round(
                    slowest_scenario_time, 4
                ),
                "slowest_scenario_name": (
                    slowest_scenario.scenario_name
                    if slowest_scenario else None
                ),
            })

        return latency_data

    def get_retry_trend(self) -> list[dict[str, Any]]:
        """Return retry history for the current tenant."""

        runs = self.execution_repository.list_by_tenant(
            self.session,
            self.tenant_id,
        )

        ordered_runs = sorted(
            runs,
            key=lambda run: run.created_at,
        )

        retry_data = []

        for run in ordered_runs:
            scenario_retries = [
                scenario.retry_count
                for scenario in run.scenario_results
            ]

            average_retries = (
                mean(scenario_retries)
                if scenario_retries else 0.0
            )

            max_retries = (
                max(scenario_retries)
                if scenario_retries else 0
            )

            max_retry_scenario = (
                max(
                    run.scenario_results,
                    key=lambda scenario: scenario.retry_count,
                )
                if run.scenario_results else None
            )

            retry_data.append({
                "run_id": str(run.run_id),
                "created_at": run.created_at.isoformat(),
                "total_retries": run.total_retries,
                "average_retries_per_scenario": round(
                    average_retries, 4
                ),
                "max_retries": max_retries,
                "max_retry_scenario_name": (
                    max_retry_scenario.scenario_name
                    if max_retry_scenario else None
                ),
            })

        return retry_data
    
    def get_fallback_trend(self) -> list[dict[str, Any]]:
        """Return fallback history for the current tenant."""

        runs = self.execution_repository.list_by_tenant(
            self.session,
            self.tenant_id,
        )

        ordered_runs = sorted(
            runs,
            key=lambda run: run.created_at,
        )

        fallback_data = []

        for run in ordered_runs:
            scenario_fallbacks = [
                scenario.fallback_count
                for scenario in run.scenario_results
            ]

            average_fallbacks = (
                mean(scenario_fallbacks)
                if scenario_fallbacks else 0.0
            )

            max_fallbacks = (
                max(scenario_fallbacks)
                if scenario_fallbacks else 0
            )

            max_fallback_scenario = (
                max(
                    run.scenario_results,
                    key=lambda scenario: scenario.fallback_count,
                )
                if run.scenario_results else None
            )

            fallback_data.append({
                "run_id": str(run.run_id),
                "created_at": run.created_at.isoformat(),
                "total_fallbacks": sum(scenario_fallbacks),
                "average_fallbacks_per_scenario": round(
                    average_fallbacks, 4
                ),
                "max_fallbacks": max_fallbacks,
                "max_fallback_scenario_name": (
                    max_fallback_scenario.scenario_name
                    if max_fallback_scenario else None
                ),
                "fallback_used": any(
                    scenario.fallback_used
                    for scenario in run.scenario_results
                ),
            })

        return fallback_data

    
    def get_circuit_breaker_trend(
        self,
    ) -> list[dict[str, Any]]:
        """Return circuit breaker usage history for the current tenant."""

        runs = self.execution_repository.list_by_tenant(
            self.session,
            self.tenant_id,
        )

        ordered_runs = sorted(
            runs,
            key=lambda run: run.created_at,
        )

        circuit_breaker_data = []

        for run in ordered_runs:
            total_scenarios = len(run.scenario_results)

            enabled_scenarios = sum(
                scenario.circuit_breaker_enabled
                for scenario in run.scenario_results
            )

            enabled_percentage = (
                (enabled_scenarios / total_scenarios) * 100
                if total_scenarios else 0.0
            )

            circuit_breaker_data.append({
                "run_id": str(run.run_id),
                "created_at": run.created_at.isoformat(),
                "total_scenarios": total_scenarios,
                "circuit_breaker_enabled_scenarios": (
                    enabled_scenarios
                ),
                "circuit_breaker_enabled_percentage": round(
                    enabled_percentage, 2
                ),
            })

        return circuit_breaker_data

    
