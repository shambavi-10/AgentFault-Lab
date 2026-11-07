from pathlib import Path
import pytest
import json

from agentfault.recommendation_engine import ReliabilityRecommendation
from agentfault.recommendation_manager import (
    RecommendationManager,
    RecommendationManagerError,
)


@pytest.fixture
def manager(tmp_path):
    return RecommendationManager(
        storage_path=tmp_path / "recommendations.json"
    )


@pytest.fixture
def sample_recommendations():
    return [
        ReliabilityRecommendation(
            experiment_id="exp-001",
            experiment_name="Unstable Agent",
            category="success",
            priority="critical",
            title="Investigate critical failures",
            description="Several scenarios failed.",
            action="Inspect execution traces.",
        ),
        ReliabilityRecommendation(
            experiment_id="exp-001",
            experiment_name="Unstable Agent",
            category="latency",
            priority="high",
            title="Optimize execution latency",
            description="Latency exceeds target.",
            action="Profile slow tool calls.",
        ),
        ReliabilityRecommendation(
            experiment_id="exp-002",
            experiment_name="Normal Agent",
            category="general",
            priority="low",
            title="Continue monitoring",
            description="No thresholds exceeded.",
            action="Continue benchmarking.",
        ),
    ]


def test_manager_creates_storage_file(tmp_path):
    path = tmp_path / "recommendations.json"

    RecommendationManager(path)

    assert path.exists()


def test_add_recommendations(manager, sample_recommendations):
    saved = manager.add_recommendations(sample_recommendations)

    assert len(saved) == 3
    assert len(manager.list_recommendations()) == 3


def test_recommendation_has_management_fields(
    manager,
    sample_recommendations,
):
    saved = manager.add_recommendations(sample_recommendations)

    item = saved[0]

    assert item["recommendation_id"]
    assert item["status"] == "open"
    assert item["assigned_to"] is None
    assert item["notes"] == []
    assert item["created_at"]
    assert item["updated_at"]
    assert item["resolved_at"] is None


def test_duplicate_recommendations_are_not_added(
    manager,
    sample_recommendations,
):
    manager.add_recommendations(sample_recommendations)
    saved_again = manager.add_recommendations(sample_recommendations)

    assert saved_again == []
    assert len(manager.list_recommendations()) == 3


def test_get_recommendation(manager, sample_recommendations):
    saved = manager.add_recommendations(sample_recommendations)

    result = manager.get_recommendation(
        saved[0]["recommendation_id"]
    )

    assert result["title"] == "Investigate critical failures"


def test_missing_recommendation_returns_none(manager):
    assert manager.get_recommendation("unknown-id") is None


def test_update_status(manager, sample_recommendations):
    saved = manager.add_recommendations(sample_recommendations)
    recommendation_id = saved[0]["recommendation_id"]

    result = manager.update_status(
        recommendation_id,
        "in_progress",
    )

    assert result["status"] == "in_progress"
    assert result["resolved_at"] is None


def test_resolve_recommendation(manager, sample_recommendations):
    saved = manager.add_recommendations(sample_recommendations)

    result = manager.update_status(
        saved[0]["recommendation_id"],
        "resolved",
    )

    assert result["status"] == "resolved"
    assert result["resolved_at"] is not None


def test_invalid_status_raises_error(manager):
    with pytest.raises(ValueError):
        manager.update_status("unknown-id", "invalid")


def test_assign_recommendation(manager, sample_recommendations):
    saved = manager.add_recommendations(sample_recommendations)

    result = manager.assign_recommendation(
        saved[0]["recommendation_id"],
        "Shambavi",
    )

    assert result["assigned_to"] == "Shambavi"


def test_add_note(manager, sample_recommendations):
    saved = manager.add_recommendations(sample_recommendations)

    result = manager.add_note(
        saved[0]["recommendation_id"],
        "Investigated the failed scenarios.",
    )

    assert len(result["notes"]) == 1
    assert result["notes"][0]["note"] == (
        "Investigated the failed scenarios."
    )


def test_filter_by_priority(manager, sample_recommendations):
    manager.add_recommendations(sample_recommendations)

    result = manager.filter_recommendations(
        priority="critical"
    )

    assert len(result) == 1
    assert result[0]["priority"] == "critical"


def test_filter_by_category(manager, sample_recommendations):
    manager.add_recommendations(sample_recommendations)

    result = manager.filter_recommendations(
        category="latency"
    )

    assert len(result) == 1
    assert result[0]["category"] == "latency"


def test_filter_by_status(manager, sample_recommendations):
    saved = manager.add_recommendations(sample_recommendations)

    manager.update_status(
        saved[0]["recommendation_id"],
        "resolved",
    )

    result = manager.filter_recommendations(
        status="resolved"
    )

    assert len(result) == 1


def test_invalid_priority_raises_error(manager):
    with pytest.raises(ValueError):
        manager.filter_recommendations(priority="urgent")


def test_invalid_filter_status_raises_error(manager):
    with pytest.raises(ValueError):
        manager.filter_recommendations(status="invalid")


def test_get_summary(manager, sample_recommendations):
    saved = manager.add_recommendations(sample_recommendations)

    manager.update_status(
        saved[0]["recommendation_id"],
        "resolved",
    )

    summary = manager.get_summary()

    assert summary["total_recommendations"] == 3
    assert summary["resolved"] == 1
    assert summary["open"] == 2
    assert summary["resolution_rate"] == pytest.approx(33.333333)


def test_empty_summary(manager):
    summary = manager.get_summary()

    assert summary["total_recommendations"] == 0
    assert summary["resolution_rate"] == 0.0


def test_recommendations_persist_between_instances(
    tmp_path,
    sample_recommendations,
):
    path = tmp_path / "recommendations.json"

    first_manager = RecommendationManager(path)
    first_manager.add_recommendations(sample_recommendations)

    second_manager = RecommendationManager(path)

    assert len(second_manager.list_recommendations()) == 3


def test_invalid_recommendation_input(manager):
    with pytest.raises(TypeError):
        manager.add_recommendations(["invalid"])


# ---------------------------------------------------------
# Additional coverage: storage error handling
# ---------------------------------------------------------

def test_load_all_with_corrupted_json(manager):
    manager.storage_path.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(
        RecommendationManagerError,
        match="Recommendation storage is corrupted",
    ):
        manager.list_recommendations()


def test_load_all_with_non_list_json(manager):
    manager.storage_path.write_text(
        json.dumps({"recommendations": []}),
        encoding="utf-8",
    )

    with pytest.raises(
        RecommendationManagerError,
        match="Recommendation storage must contain a JSON list",
    ):
        manager.list_recommendations()


def test_load_all_with_os_error(manager, monkeypatch):
    original_open = Path.open

    def failing_open(self, mode="r", *args, **kwargs):
        if self == manager.storage_path and mode == "r":
            raise OSError("Simulated read failure")

        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)

    with pytest.raises(
        RecommendationManagerError,
        match="Unable to read recommendation storage",
    ):
        manager.list_recommendations()


def test_save_all_with_os_error(manager, monkeypatch):
    original_open = Path.open

    def failing_open(self, mode="r", *args, **kwargs):
        if self == manager.storage_path and mode == "w":
            raise OSError("Simulated write failure")

        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)

    with pytest.raises(
        RecommendationManagerError,
        match="Unable to save recommendations",
    ):
        manager._save_all([])


# ---------------------------------------------------------
# Additional coverage: input validation
# ---------------------------------------------------------

def test_add_recommendations_rejects_non_list(manager):
    with pytest.raises(
        TypeError,
        match="Expected a list of recommendations",
    ):
        manager.add_recommendations("invalid")


def test_add_recommendations_rejects_invalid_item(manager):
    with pytest.raises(
        TypeError,
        match="All items must be ReliabilityRecommendation instances",
    ):
        manager.add_recommendations([{"title": "Invalid"}])


# ---------------------------------------------------------
# Additional coverage: missing recommendation handling
# ---------------------------------------------------------

def test_update_status_for_missing_recommendation(manager):
    with pytest.raises(
        RecommendationManagerError,
        match="Recommendation not found: unknown-id",
    ):
        manager.update_status("unknown-id", "resolved")


def test_assign_missing_recommendation(manager):
    with pytest.raises(
        RecommendationManagerError,
        match="Recommendation not found: unknown-id",
    ):
        manager.assign_recommendation("unknown-id", "Owner")


def test_add_note_to_missing_recommendation(manager):
    with pytest.raises(
        RecommendationManagerError,
        match="Recommendation not found: unknown-id",
    ):
        manager.add_note("unknown-id", "Test note")


# ---------------------------------------------------------
# Additional coverage: filtering combinations
# ---------------------------------------------------------

def test_filter_by_multiple_criteria(manager, sample_recommendations):
    manager.add_recommendations(sample_recommendations)

    result = manager.filter_recommendations(
        priority="critical",
        category="success",
        status="open",
    )

    assert len(result) == 1
    assert result[0]["priority"] == "critical"
    assert result[0]["category"] == "success"
    assert result[0]["status"] == "open"


def test_filter_returns_empty_for_non_matching_criteria(
    manager,
    sample_recommendations,
):
    manager.add_recommendations(sample_recommendations)

    result = manager.filter_recommendations(
        priority="critical",
        category="latency",
        status="resolved",
    )

    assert result == []


def test_filter_with_no_criteria_returns_all(
    manager,
    sample_recommendations,
):
    manager.add_recommendations(sample_recommendations)

    result = manager.filter_recommendations()

    assert len(result) == 3


# ---------------------------------------------------------
# Additional coverage: recommendation summary
# ---------------------------------------------------------

def test_summary_contains_all_priority_counts(
    manager,
    sample_recommendations,
):
    manager.add_recommendations(sample_recommendations)

    summary = manager.get_summary()

    assert summary["priority_counts"] == {
        "critical": 1,
        "high": 1,
        "medium": 0,
        "low": 1,
    }


def test_summary_after_all_recommendations_are_resolved(
    manager,
    sample_recommendations,
):
    saved = manager.add_recommendations(sample_recommendations)

    for item in saved:
        manager.update_status(
            item["recommendation_id"],
            "resolved",
        )

    summary = manager.get_summary()

    assert summary["total_recommendations"] == 3
    assert summary["resolved"] == 3
    assert summary["open"] == 0
    assert summary["in_progress"] == 0
    assert summary["resolution_rate"] == 100.0


def test_get_recommendation_rejects_empty_id(manager):
    with pytest.raises(
        ValueError,
        match="Recommendation ID cannot be empty",
    ):
        manager.get_recommendation("")


def test_assign_recommendation_rejects_empty_assignee(manager):
    with pytest.raises(
        ValueError,
        match="Assignee cannot be empty",
    ):
        manager.assign_recommendation("unknown-id", "   ")


def test_add_note_rejects_empty_note(manager):
    with pytest.raises(
        ValueError,
        match="Note cannot be empty",
    ):
        manager.add_note("unknown-id", "   ")
