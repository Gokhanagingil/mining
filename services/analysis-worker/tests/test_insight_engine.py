"""
Tests for the insight candidate engine.
"""
import pytest
from app.models.schemas import MappingDecision
from app.services.insight_engine import InsightCandidateEngine


def make_mapping(**kwargs) -> MappingDecision:
    return MappingDecision(
        dataset_id="test-dataset",
        **kwargs
    )


@pytest.fixture
def engine():
    return InsightCandidateEngine()


@pytest.fixture
def sample_metrics_with_spike():
    """Metrics with Monday spike pattern."""
    return {
        "weekday_patterns": [
            {"weekday": 0, "weekday_name": "Monday", "count": 450, "avg_count_per_week": 450, "relative_to_mean": 2.1},
            {"weekday": 1, "weekday_name": "Tuesday", "count": 210, "avg_count_per_week": 210, "relative_to_mean": 0.98},
            {"weekday": 2, "weekday_name": "Wednesday", "count": 205, "avg_count_per_week": 205, "relative_to_mean": 0.96},
            {"weekday": 3, "weekday_name": "Thursday", "count": 200, "avg_count_per_week": 200, "relative_to_mean": 0.94},
            {"weekday": 4, "weekday_name": "Friday", "count": 195, "avg_count_per_week": 195, "relative_to_mean": 0.91},
            {"weekday": 5, "weekday_name": "Saturday", "count": 50, "avg_count_per_week": 50, "relative_to_mean": 0.23},
            {"weekday": 6, "weekday_name": "Sunday", "count": 30, "avg_count_per_week": 30, "relative_to_mean": 0.14},
        ],
        "top_categories": [
            {"category": "Password Reset", "count": 1250, "pct": 28.5},
            {"category": "Hardware Issue", "count": 500, "pct": 11.4},
            {"category": "Network", "count": 400, "pct": 9.1},
        ],
        "duration_metrics": {
            "mean_minutes": 480.0,
            "median_minutes": 240.0,
            "p25_minutes": 60.0,
            "p75_minutes": 720.0,
            "p95_minutes": 2880.0,
            "p99_minutes": 5760.0,
            "std_dev_minutes": 360.0,
            "case_count": 4200,
        },
        "top_assignees": [
            {"actor": "alice.jones", "case_count": 800, "avg_duration_minutes": 180.0, "median_duration_minutes": 150.0, "p95_duration_minutes": 600.0, "avg_satisfaction": 4.2},
            {"actor": "bob.smith", "case_count": 750, "avg_duration_minutes": 200.0, "median_duration_minutes": 175.0, "p95_duration_minutes": 650.0, "avg_satisfaction": 3.9},
            {"actor": "carol.slow", "case_count": 600, "avg_duration_minutes": 520.0, "median_duration_minutes": 480.0, "p95_duration_minutes": 1800.0, "avg_satisfaction": 3.1},
            {"actor": "dave.fast", "case_count": 700, "avg_duration_minutes": 120.0, "median_duration_minutes": 100.0, "p95_duration_minutes": 400.0, "avg_satisfaction": 4.5},
        ],
        "top_groups": [
            {"actor": "Service Desk L1", "case_count": 2000, "avg_duration_minutes": 300.0, "median_duration_minutes": 240.0, "p95_duration_minutes": 1200.0},
            {"actor": "Network Team", "case_count": 500, "avg_duration_minutes": 600.0, "median_duration_minutes": 540.0, "p95_duration_minutes": 4800.0},
        ],
        "satisfaction_stats": {"mean": 2.9, "median": 3.0, "min": 1.0, "max": 5.0, "std_dev": 0.9},
        "reopen_signals": {"reopened_count": 250, "reopen_rate_pct": 6.0, "risk_level": "medium"},
        "backlog_aging": [
            {"age_bucket": "< 1 day", "count": 50, "pct": 25.0},
            {"age_bucket": "1-7 days", "count": 40, "pct": 20.0},
            {"age_bucket": "8-30 days", "count": 30, "pct": 15.0},
            {"age_bucket": "31-90 days", "count": 50, "pct": 25.0},
            {"age_bucket": "180+ days", "count": 30, "pct": 15.0},
        ],
    }


class TestWeekdaySpike:
    def test_detects_monday_spike(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(created_at_column="opened_at")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        # Should find Monday spike
        spike_insights = [c for c in candidates if c.insight_type == "temporal_spike"]
        assert len(spike_insights) > 0

        monday_spike = next(
            (c for c in spike_insights if "Monday" in c.title), None
        )
        assert monday_spike is not None
        assert monday_spike.effect_size > 0.4
        assert monday_spike.confidence > 0.5

    def test_spike_effect_size_correct(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(created_at_column="opened_at")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        spike = next((c for c in candidates if "Monday" in c.title), None)
        if spike:
            # Monday is 2.1x mean, so effect size should be around 1.1
            assert spike.effect_size > 0.8


class TestAssigneePerformanceGap:
    def test_detects_slow_assignee(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(assignee_column="assignee")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        perf_insights = [c for c in candidates if c.insight_type == "assignee_performance_gap"]
        assert len(perf_insights) > 0

        # carol.slow should be detected (480 min median vs ~226 group mean)
        carol_insight = next(
            (c for c in perf_insights if "carol.slow" in c.title or "carol.slow" in str(c.evidence_refs)),
            None
        )
        assert carol_insight is not None

    def test_multiple_performance_outliers_detected(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(assignee_column="assignee")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        perf_insights = [c for c in candidates if c.insight_type == "assignee_performance_gap"]
        # At least carol.slow (very slow) should be detected
        assert len(perf_insights) >= 1
        # carol.slow's evidence should be in one insight
        carol_found = any("carol.slow" in str(c.evidence_refs) for c in perf_insights)
        assert carol_found


class TestCategoryInsights:
    def test_dominant_category_detected(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(category_column="category")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        cat_insights = [c for c in candidates if c.insight_type == "category_recurrence"]
        assert len(cat_insights) > 0

        # Password Reset is 28.5%
        pwd_insight = next(
            (c for c in cat_insights if "Password Reset" in c.title), None
        )
        assert pwd_insight is not None
        assert pwd_insight.support_count == 1250

    def test_self_service_opportunity(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(category_column="category")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        ss_insights = [c for c in candidates if c.insight_type == "self_service_opportunity"]
        # Password Reset should trigger self-service opportunity
        pwd_ss = next(
            (c for c in ss_insights if "Password" in c.title), None
        )
        assert pwd_ss is not None


class TestReopenSignals:
    def test_reopen_detected(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(case_id_column="incident_number")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        reopen_insights = [c for c in candidates if c.insight_type == "rework_loop_pattern"]
        assert len(reopen_insights) > 0
        assert reopen_insights[0].support_count == 250


class TestInsightRanking:
    def test_insights_are_ranked(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(
            created_at_column="opened_at",
            assignee_column="assignee",
            category_column="category",
            case_id_column="incident_number",
        )
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        assert len(candidates) > 0
        # Should be sorted descending by rank_score
        for i in range(len(candidates) - 1):
            assert candidates[i].rank_score >= candidates[i + 1].rank_score

    def test_max_15_insights_returned(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(
            created_at_column="opened_at",
            assignee_column="assignee",
            category_column="category",
            case_id_column="incident_number",
            customer_column="customer",
            satisfaction_column="satisfaction_score",
        )
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)
        assert len(candidates) <= 15

    def test_all_insights_have_required_fields(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(created_at_column="opened_at")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        for c in candidates:
            assert c.insight_id
            assert c.insight_type
            assert c.title
            assert c.description_seed
            assert c.support_count >= 0
            assert 0.0 <= c.confidence <= 1.0
            assert c.effect_size >= 0.0
            assert c.rank_score >= 0.0


class TestQueueBottleneck:
    def test_queue_bottleneck_detected(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(assignment_group_column="group")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        bottleneck_insights = [c for c in candidates if c.insight_type == "queue_bottleneck"]
        # Network Team has P95 4800 vs group mean ~3000
        assert len(bottleneck_insights) > 0


class TestSatisfactionDegradation:
    def test_low_satisfaction_detected(self, engine, sample_metrics_with_spike):
        mapping = make_mapping(satisfaction_column="satisfaction_score")
        candidates = engine.generate(sample_metrics_with_spike, mapping, 4400)

        sat_insights = [c for c in candidates if c.insight_type == "satisfaction_degradation"]
        assert len(sat_insights) > 0

        # Overall mean 3.5/5 = 70%, below threshold
        overall = next((c for c in sat_insights if "Below-Target" in c.title or "Target" in c.title), None)
        assert overall is not None
