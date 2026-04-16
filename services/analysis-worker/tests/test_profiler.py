"""
Tests for the CSV profiling engine.
Uses the demo datasets from /workspace/datasets.
"""
import os
import tempfile
import pytest
import csv
from app.services.profiler import CSVProfiler


@pytest.fixture
def tmp_storage(tmp_path):
    storage = tmp_path / "storage"
    parquet = tmp_path / "parquet"
    storage.mkdir()
    parquet.mkdir()
    return storage, parquet


@pytest.fixture
def profiler(tmp_storage):
    storage, parquet = tmp_storage
    return CSVProfiler(
        storage_path=str(storage),
        parquet_base=str(parquet),
        sample_size=1000,
    )


def write_csv(path: str, rows: list[dict]):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


class TestCSVProfilerBasic:
    def test_profiles_simple_csv(self, profiler, tmp_path):
        csv_path = str(tmp_path / "test.csv")
        rows = [
            {"id": str(i), "name": f"User {i}", "score": str(i * 1.5), "status": "open"}
            for i in range(100)
        ]
        write_csv(csv_path, rows)

        result = profiler.profile(csv_path, "test-dataset")

        assert result.row_count == 100
        assert result.column_count == 4
        assert result.delimiter == ","
        assert result.has_header is True

    def test_column_profiles_complete(self, profiler, tmp_path):
        csv_path = str(tmp_path / "test.csv")
        rows = [
            {"id": str(i), "category": "Software", "value": str(float(i))}
            for i in range(50)
        ]
        write_csv(csv_path, rows)

        result = profiler.profile(csv_path, "dataset-2")

        assert len(result.columns) == 3
        col_names = {c.column_name for c in result.columns}
        assert col_names == {"id", "category", "value"}

    def test_null_detection(self, profiler, tmp_path):
        csv_path = str(tmp_path / "nulls.csv")
        rows = [{"id": str(i), "optional": "" if i % 3 == 0 else f"val{i}"} for i in range(90)]
        write_csv(csv_path, rows)

        result = profiler.profile(csv_path, "null-test")

        optional_col = next(c for c in result.columns if c.column_name == "optional")
        assert optional_col.null_ratio > 0.25
        assert optional_col.null_ratio < 0.45

    def test_distinct_count_accurate(self, profiler, tmp_path):
        csv_path = str(tmp_path / "distinct.csv")
        categories = ["A", "B", "C", "D", "E"]
        rows = [{"cat": categories[i % 5]} for i in range(200)]
        write_csv(csv_path, rows)

        result = profiler.profile(csv_path, "distinct-test")

        cat_col = next(c for c in result.columns if c.column_name == "cat")
        assert cat_col.distinct_count == 5
        assert cat_col.is_enum_like is True

    def test_numeric_stats(self, profiler, tmp_path):
        csv_path = str(tmp_path / "numeric.csv")
        rows = [{"score": str(i)} for i in range(1, 101)]
        write_csv(csv_path, rows)

        result = profiler.profile(csv_path, "numeric-test")

        score_col = next(c for c in result.columns if c.column_name == "score")
        assert score_col.inferred_type == "integer"
        assert score_col.mean_value is not None
        assert abs(score_col.mean_value - 50.5) < 2.0

    def test_timestamp_detection(self, profiler, tmp_path):
        csv_path = str(tmp_path / "timestamps.csv")
        rows = [
            {"id": str(i), "created_at": f"2024-01-{i%28+1:02d} 09:00:00"}
            for i in range(100)
        ]
        write_csv(csv_path, rows)

        result = profiler.profile(csv_path, "ts-test")

        ts_col = next(c for c in result.columns if c.column_name == "created_at")
        assert ts_col.timestamp_parse_success_ratio is not None
        assert ts_col.timestamp_parse_success_ratio > 0.5


class TestSemanticInferenceIntegration:
    def test_helpdesk_schema_inferred(self, profiler, tmp_path):
        csv_path = str(tmp_path / "helpdesk.csv")
        rows = [
            {
                "incident_number": f"INC{i}",
                "category": "Password Reset",
                "priority": "P2 - High",
                "state": "Closed",
                "opened_at": "2024-01-15 09:00:00",
                "resolved_at": "2024-01-15 11:30:00",
                "assigned_to": "john.smith",
                "assignment_group": "Service Desk L1",
                "satisfaction_score": "4.0",
            }
            for i in range(50)
        ]
        write_csv(csv_path, rows)

        result = profiler.profile(csv_path, "helpdesk-test")

        assert len(result.semantic_inferences) == 9
        inf_map = {inf.column_name: inf for inf in result.semantic_inferences}

        assert inf_map["assigned_to"].inferred_role.value == "assignee"
        assert inf_map["assignment_group"].inferred_role.value == "assignment_group"

    def test_readiness_score_computed(self, profiler, tmp_path):
        csv_path = str(tmp_path / "good_data.csv")
        rows = [
            {
                "ticket_id": f"T{i}",
                "created_at": "2024-01-15 09:00:00",
                "resolved_at": "2024-01-15 11:30:00",
                "assignee": "john.smith",
                "category": "Hardware",
                "status": "Closed",
            }
            for i in range(50)
        ]
        write_csv(csv_path, rows)

        result = profiler.profile(csv_path, "readiness-test")

        assert result.process_readiness is not None
        assert 0 <= result.process_readiness.overall <= 100
        assert isinstance(result.process_readiness.warnings, list)


class TestDemoDatasets:
    """Test against the actual generated demo datasets."""

    demo_path = "/workspace/datasets"

    @pytest.mark.skipif(
        not os.path.exists("/workspace/datasets/password-reset-spike.csv"),
        reason="Demo dataset not found"
    )
    def test_password_reset_spike_dataset(self, profiler):
        result = profiler.profile(
            f"{self.demo_path}/password-reset-spike.csv",
            "demo-1"
        )
        assert result.row_count == 5000
        assert result.column_count > 5

        # Should detect timestamp columns
        ts_cols = [
            inf for inf in result.semantic_inferences
            if inf.inferred_role.value in ("created_at", "updated_at", "resolved_at", "closed_at")
        ]
        assert len(ts_cols) >= 1

        # Readiness should be reasonable
        assert result.process_readiness.overall > 30

    @pytest.mark.skipif(
        not os.path.exists("/workspace/datasets/customer-assignee-performance.csv"),
        reason="Demo dataset not found"
    )
    def test_customer_assignee_dataset(self, profiler):
        result = profiler.profile(
            f"{self.demo_path}/customer-assignee-performance.csv",
            "demo-2"
        )
        assert result.row_count == 4000
        assert result.column_count > 5

        # Should detect assignee and customer columns
        inf_map = {inf.column_name: inf for inf in result.semantic_inferences}
        assert any(
            inf.inferred_role.value == "assignee"
            for inf in result.semantic_inferences
        )
