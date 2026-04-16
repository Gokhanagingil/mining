"""
Tests for the semantic column inference engine.
"""
import pytest
from app.models.schemas import ColumnProfile, SemanticRole
from app.services.semantic_inference import SemanticInferenceEngine


def make_col(
    name: str,
    inferred_type: str = "string",
    distinct_count: int = 100,
    distinct_ratio: float = 0.5,
    null_ratio: float = 0.0,
    is_enum_like: bool = False,
    is_free_text: bool = False,
    sample_values: list = None,
    timestamp_parse_success_ratio: float = None,
    min_value: str = None,
    max_value: str = None,
) -> ColumnProfile:
    return ColumnProfile(
        column_name=name,
        inferred_type=inferred_type,
        null_count=int(null_ratio * 1000),
        null_ratio=null_ratio,
        distinct_count=distinct_count,
        distinct_ratio=distinct_ratio,
        is_enum_like=is_enum_like,
        is_free_text=is_free_text,
        sample_values=sample_values or [],
        min_value=min_value,
        max_value=max_value,
        timestamp_parse_success_ratio=timestamp_parse_success_ratio,
    )


@pytest.fixture
def engine():
    return SemanticInferenceEngine()


class TestCaseIdInference:
    def test_incident_number(self, engine):
        cols = [make_col("incident_number", inferred_type="identifier", distinct_count=5000, distinct_ratio=0.9)]
        results = engine.infer(cols)
        assert results[0].inferred_role in (SemanticRole.case_id, SemanticRole.record_id)
        assert results[0].confidence > 0.5

    def test_ticket_id(self, engine):
        cols = [make_col("ticket_id", inferred_type="identifier")]
        results = engine.infer(cols)
        assert results[0].inferred_role in (SemanticRole.case_id, SemanticRole.record_id)
        assert results[0].confidence > 0.6


class TestTimestampInference:
    def test_opened_at(self, engine):
        cols = [make_col("opened_at", inferred_type="datetime", timestamp_parse_success_ratio=0.98)]
        results = engine.infer(cols)
        assert results[0].inferred_role == SemanticRole.created_at
        assert results[0].confidence > 0.7

    def test_resolved_at(self, engine):
        cols = [make_col("resolved_at", inferred_type="datetime", timestamp_parse_success_ratio=0.95)]
        results = engine.infer(cols)
        assert results[0].inferred_role == SemanticRole.resolved_at
        assert results[0].confidence > 0.7

    def test_created_at_exact(self, engine):
        cols = [make_col("created_at", inferred_type="datetime")]
        results = engine.infer(cols)
        assert results[0].inferred_role == SemanticRole.created_at
        assert results[0].confidence > 0.9


class TestStatusInference:
    def test_state_column(self, engine):
        cols = [make_col("state", inferred_type="categorical", is_enum_like=True,
                         sample_values=["Open", "Closed", "In Progress", "Pending"])]
        results = engine.infer(cols)
        assert results[0].inferred_role in (SemanticRole.status, SemanticRole.state)
        assert results[0].confidence > 0.7

    def test_status_values(self, engine):
        cols = [make_col("incident_state", inferred_type="categorical", is_enum_like=True,
                         sample_values=["open", "resolved", "closed", "pending"])]
        results = engine.infer(cols)
        assert results[0].inferred_role in (SemanticRole.status, SemanticRole.state)


class TestAssigneeInference:
    def test_assigned_to(self, engine):
        cols = [make_col("assigned_to", inferred_type="string")]
        results = engine.infer(cols)
        assert results[0].inferred_role == SemanticRole.assignee
        assert results[0].confidence > 0.7

    def test_assignment_group(self, engine):
        cols = [make_col("assignment_group", inferred_type="categorical", is_enum_like=True)]
        results = engine.infer(cols)
        assert results[0].inferred_role == SemanticRole.assignment_group
        assert results[0].confidence > 0.7


class TestSatisfactionInference:
    def test_satisfaction_score_name(self, engine):
        cols = [make_col("satisfaction_score", inferred_type="float",
                         min_value="1.0", max_value="5.0", distinct_count=5)]
        results = engine.infer(cols)
        assert results[0].inferred_role == SemanticRole.satisfaction_score
        assert results[0].confidence > 0.7

    def test_numeric_scale_values(self, engine):
        cols = [make_col("csat", inferred_type="integer",
                         min_value="1", max_value="10", distinct_count=10)]
        results = engine.infer(cols)
        assert results[0].inferred_role == SemanticRole.satisfaction_score
        assert results[0].confidence > 0.6


class TestCategoryInference:
    def test_category_column(self, engine):
        cols = [make_col("category", inferred_type="categorical", is_enum_like=True,
                         sample_values=["Hardware", "Software", "Network", "Password"])]
        results = engine.infer(cols)
        assert results[0].inferred_role == SemanticRole.category
        assert results[0].confidence > 0.7

    def test_priority_values(self, engine):
        cols = [make_col("priority", inferred_type="categorical", is_enum_like=True,
                         sample_values=["high", "medium", "low", "critical"])]
        results = engine.infer(cols)
        assert results[0].inferred_role == SemanticRole.priority
        assert results[0].confidence > 0.8


class TestFreeTextInference:
    def test_description_column(self, engine):
        cols = [make_col("short_description", inferred_type="string", is_free_text=True,
                         distinct_ratio=0.9, distinct_count=900)]
        results = engine.infer(cols)
        assert results[0].inferred_role in (SemanticRole.description, SemanticRole.comment_text)

    def test_unknown_column(self, engine):
        cols = [make_col("xyz_col_123", inferred_type="string",
                         sample_values=["abc", "def"])]
        results = engine.infer(cols)
        # Should still produce some result (may be unknown)
        assert results[0].inferred_role is not None


class TestMultiColumnInference:
    def test_full_helpdesk_schema(self, engine):
        cols = [
            make_col("incident_number", inferred_type="identifier", distinct_count=5000),
            make_col("category", inferred_type="categorical", is_enum_like=True,
                     sample_values=["Hardware", "Software", "Network"]),
            make_col("priority", inferred_type="categorical", is_enum_like=True,
                     sample_values=["high", "medium", "low"]),
            make_col("state", inferred_type="categorical", is_enum_like=True,
                     sample_values=["Open", "Closed", "Pending"]),
            make_col("opened_at", inferred_type="datetime", timestamp_parse_success_ratio=0.99),
            make_col("resolved_at", inferred_type="datetime", timestamp_parse_success_ratio=0.95),
            make_col("assigned_to", inferred_type="string"),
            make_col("assignment_group", inferred_type="categorical", is_enum_like=True),
            make_col("satisfaction_score", inferred_type="float", min_value="1", max_value="5", distinct_count=9),
        ]
        results = engine.infer(cols)
        assert len(results) == len(cols)

        role_map = {r.column_name: r.inferred_role for r in results}

        assert role_map["opened_at"] == SemanticRole.created_at
        assert role_map["resolved_at"] == SemanticRole.resolved_at
        assert role_map["assigned_to"] == SemanticRole.assignee
        assert role_map["assignment_group"] == SemanticRole.assignment_group
        assert role_map["satisfaction_score"] == SemanticRole.satisfaction_score
        assert role_map["category"] == SemanticRole.category
        assert role_map["priority"] == SemanticRole.priority
