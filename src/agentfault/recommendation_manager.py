import json
import uuid

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from agentfault.recommendation_engine import (
    ReliabilityRecommendation,
)


class RecommendationManagerError(Exception):
    """Raised when recommendation management operations fail."""


class RecommendationManager:
    """Manages persistent reliability recommendations."""

    VALID_STATUSES = {
        "open",
        "in_progress",
        "resolved",
    }

    VALID_PRIORITIES = {
        "critical",
        "high",
        "medium",
        "low",
    }

    def __init__(
        self,
        storage_path: str | Path = "recommendations.json",
    ):
        self.storage_path = Path(storage_path)

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.storage_path.exists():
            self._save_all([])

    def _get_timestamp(self) -> str:
        """Return the current UTC timestamp."""

        return datetime.now(timezone.utc).isoformat()

    def _load_all(self) -> list[dict]:
        """Load all saved recommendations."""

        try:
            with self.storage_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if not isinstance(data, list):
                raise RecommendationManagerError(
                    "Recommendation storage must contain a JSON list"
                )

            return data

        except json.JSONDecodeError as exc:
            raise RecommendationManagerError(
                "Recommendation storage is corrupted"
            ) from exc

        except OSError as exc:
            raise RecommendationManagerError(
                "Unable to read recommendation storage"
            ) from exc

    def _save_all(self, recommendations: list[dict]) -> None:
        """Persist all recommendations."""

        try:
            with self.storage_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    recommendations,
                    file,
                    indent=4,
                )

        except OSError as exc:
            raise RecommendationManagerError(
                "Unable to save recommendations"
            ) from exc

    def add_recommendations(
        self,
        recommendations: list[ReliabilityRecommendation],
    ) -> list[dict]:
        """Save a collection of generated recommendations."""

        if not isinstance(recommendations, list):
            raise TypeError("Expected a list of recommendations")

        for recommendation in recommendations:
            if not isinstance(
                recommendation,
                ReliabilityRecommendation,
            ):
                raise TypeError(
                    "All items must be ReliabilityRecommendation instances"
                )

        saved = self._load_all()
        created = []

        existing_keys = {
            (
                item["experiment_id"],
                item["category"],
                item["title"],
            )
            for item in saved
        }

        for recommendation in recommendations:
            key = (
                recommendation.experiment_id,
                recommendation.category,
                recommendation.title,
            )

            if key in existing_keys:
                continue

            record = asdict(recommendation)

            timestamp = self._get_timestamp()

            record.update({
                "recommendation_id": str(uuid.uuid4()),
                "status": "open",
                "assigned_to": None,
                "notes": [],
                "created_at": timestamp,
                "updated_at": timestamp,
                "resolved_at": None,
            })

            saved.append(record)
            created.append(record)
            existing_keys.add(key)

        self._save_all(saved)

        return created

    def list_recommendations(self) -> list[dict]:
        """Return all saved recommendations."""

        return self._load_all()

    def get_recommendation(
        self,
        recommendation_id: str,
    ) -> dict | None:
        """Retrieve one recommendation by its ID."""

        if not recommendation_id or not recommendation_id.strip():
            raise ValueError("Recommendation ID cannot be empty")

        return next(
            (
                item
                for item in self._load_all()
                if item.get("recommendation_id") == recommendation_id
            ),
            None,
        )

    def update_status(
        self,
        recommendation_id: str,
        status: str,
    ) -> dict:
        """Update the lifecycle status of a recommendation."""

        if status not in self.VALID_STATUSES:
            raise ValueError("Invalid recommendation status")

        recommendations = self._load_all()

        for item in recommendations:
            if item["recommendation_id"] == recommendation_id:
                item["status"] = status
                item["updated_at"] = self._get_timestamp()

                item["resolved_at"] = (
                    self._get_timestamp()
                    if status == "resolved"
                    else None
                )

                self._save_all(recommendations)
                return item

        raise RecommendationManagerError(
            f"Recommendation not found: {recommendation_id}"
        )

    def assign_recommendation(
        self,
        recommendation_id: str,
        assigned_to: str,
    ) -> dict:
        """Assign a recommendation to an owner."""

        if not assigned_to or not assigned_to.strip():
            raise ValueError("Assignee cannot be empty")

        recommendations = self._load_all()

        for item in recommendations:
            if item["recommendation_id"] == recommendation_id:
                item["assigned_to"] = assigned_to.strip()
                item["updated_at"] = self._get_timestamp()

                self._save_all(recommendations)
                return item

        raise RecommendationManagerError(
            f"Recommendation not found: {recommendation_id}"
        )

    def add_note(
        self,
        recommendation_id: str,
        note: str,
    ) -> dict:
        """Add a progress note to a recommendation."""

        if not note or not note.strip():
            raise ValueError("Note cannot be empty")

        recommendations = self._load_all()

        for item in recommendations:
            if item["recommendation_id"] == recommendation_id:
                item["notes"].append({
                    "note": note.strip(),
                    "created_at": self._get_timestamp(),
                })

                item["updated_at"] = self._get_timestamp()

                self._save_all(recommendations)
                return item

        raise RecommendationManagerError(
            f"Recommendation not found: {recommendation_id}"
        )

    def filter_recommendations(
        self,
        priority: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """Filter recommendations using optional criteria."""

        if priority is not None and priority not in self.VALID_PRIORITIES:
            raise ValueError("Invalid recommendation priority")

        if status is not None and status not in self.VALID_STATUSES:
            raise ValueError("Invalid recommendation status")

        recommendations = self._load_all()

        return [
            item
            for item in recommendations
            if (priority is None or item["priority"] == priority)
            and (category is None or item["category"] == category)
            and (status is None or item["status"] == status)
        ]

    def get_summary(self) -> dict:
        """Generate recommendation management statistics."""

        recommendations = self._load_all()

        total = len(recommendations)

        status_counts = {
            status: sum(
                1
                for item in recommendations
                if item["status"] == status
            )
            for status in self.VALID_STATUSES
        }

        priority_counts = {
            priority: sum(
                1
                for item in recommendations
                if item["priority"] == priority
            )
            for priority in self.VALID_PRIORITIES
        }

        resolved = status_counts["resolved"]

        return {
            "total_recommendations": total,
            "open": status_counts["open"],
            "in_progress": status_counts["in_progress"],
            "resolved": resolved,
            "resolution_rate": (
                resolved / total * 100
                if total
                else 0.0
            ),
            "priority_counts": priority_counts,
        }
