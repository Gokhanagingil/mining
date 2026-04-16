"""
Deterministic Metrics Engine

All metrics computed via DuckDB queries over Parquet files.
No randomness. No LLM. Pure SQL + math.
"""
import logging
import uuid
import math
from datetime import datetime, timezone
from typing import Any, Optional
import duckdb
from app.models.schemas import MappingDecision

logger = logging.getLogger(__name__)


def _safe(col: Optional[str]) -> Optional[str]:
    if col:
        return f'"{col}"'
    return None


class MetricsEngine:
    def __init__(self, parquet_path: str):
        self.parquet_path = parquet_path
        self.con = duckdb.connect()
        self.con.execute(f"CREATE VIEW dataset AS SELECT * FROM '{parquet_path}'")

    def close(self):
        self.con.close()

    def _get_row_count(self) -> int:
        res = self.con.execute("SELECT COUNT(*) FROM dataset").fetchone()
        return res[0] if res else 0

    def compute_all(self, mapping: MappingDecision) -> dict[str, Any]:
        metrics: dict[str, Any] = {}
        row_count = self._get_row_count()

        # Volume over time
        if mapping.created_at_column:
            metrics["volume_over_time"] = self._volume_over_time(mapping.created_at_column)
            metrics["weekday_patterns"] = self._weekday_patterns(mapping.created_at_column)
            metrics["hourly_patterns"] = self._hourly_patterns(mapping.created_at_column)

        # Duration metrics
        duration_col = mapping.resolved_at_column or mapping.closed_at_column
        if mapping.created_at_column and duration_col:
            metrics["duration_metrics"] = self._duration_metrics(
                mapping.created_at_column, duration_col
            )
            metrics["category_duration"] = self._category_duration(
                mapping.created_at_column, duration_col, mapping.category_column
            )

        # Category breakdown
        if mapping.category_column:
            metrics["top_categories"] = self._top_categories(mapping.category_column, row_count)

        # Subcategory breakdown
        if mapping.subcategory_column:
            metrics["top_subcategories"] = self._top_categories(mapping.subcategory_column, row_count)

        # Assignee metrics
        if mapping.assignee_column:
            metrics["top_assignees"] = self._actor_metrics(
                mapping.assignee_column, mapping.created_at_column,
                duration_col, mapping.satisfaction_column, row_count
            )

        # Group metrics
        if mapping.assignment_group_column:
            metrics["top_groups"] = self._actor_metrics(
                mapping.assignment_group_column, mapping.created_at_column,
                duration_col, mapping.satisfaction_column, row_count
            )

        # Customer metrics
        if mapping.customer_column:
            metrics["top_customers"] = self._actor_metrics(
                mapping.customer_column, mapping.created_at_column,
                duration_col, mapping.satisfaction_column, row_count
            )

        # Status distribution
        if mapping.status_column:
            metrics["status_distribution"] = self._top_categories(mapping.status_column, row_count)

        # Priority distribution
        if mapping.priority_column:
            metrics["priority_distribution"] = self._top_categories(mapping.priority_column, row_count)

        # Overall satisfaction
        if mapping.satisfaction_column:
            metrics["satisfaction_stats"] = self._satisfaction_stats(mapping.satisfaction_column)

        # SLA breach rate
        if mapping.satisfaction_column:
            pass  # computed in satisfaction stats

        # Outlier cases
        if mapping.case_id_column and mapping.created_at_column and duration_col:
            metrics["outlier_cases"] = self._outlier_cases(
                mapping.case_id_column, mapping.created_at_column, duration_col,
                mapping.category_column, mapping.assignee_column
            )

        # Backlog aging (cases without resolved date)
        if mapping.created_at_column:
            metrics["backlog_aging"] = self._backlog_aging(
                mapping.created_at_column, mapping.status_column
            )

        # Cross-comparison: customer × assignee performance
        if mapping.customer_column and mapping.assignee_column and duration_col:
            metrics["customer_assignee_matrix"] = self._cross_comparison(
                mapping.customer_column, mapping.assignee_column,
                mapping.created_at_column, duration_col, row_count
            )

        # Reopen signals (look for patterns in status transitions)
        if mapping.case_id_column and mapping.status_column:
            metrics["reopen_signals"] = self._reopen_signals(
                mapping.case_id_column, mapping.status_column, row_count
            )

        # SLA breach rate
        sla_col = self._find_sla_col(mapping)
        if sla_col:
            metrics["sla_breach_rate"] = self._sla_breach_rate(sla_col, row_count)

        return metrics

    def _find_sla_col(self, mapping: MappingDecision) -> Optional[str]:
        # Check additional_dimensions for sla_breach_flag
        if mapping.additional_dimensions:
            for k, v in mapping.additional_dimensions.items():
                if "sla" in k.lower() or "breach" in k.lower():
                    return v
        return None

    def _volume_over_time(self, ts_col: str) -> list[dict]:
        try:
            res = self.con.execute(f"""
                SELECT
                    DATE_TRUNC('month', TRY_STRPTIME(CAST("{ts_col}" AS VARCHAR), '%Y-%m-%d %H:%M:%S')) AS period,
                    COUNT(*) as count
                FROM dataset
                WHERE "{ts_col}" IS NOT NULL
                GROUP BY 1
                ORDER BY 1
                LIMIT 60
            """).fetchall()
            if not res or res[0][0] is None:
                # Try other format
                res = self.con.execute(f"""
                    SELECT
                        DATE_TRUNC('month', CAST("{ts_col}" AS TIMESTAMP)) AS period,
                        COUNT(*) as count
                    FROM dataset
                    WHERE "{ts_col}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY 1
                    LIMIT 60
                """).fetchall()
            items = [{"period": str(r[0])[:7] if r[0] else "unknown", "count": int(r[1])} for r in res if r[0]]
            # Add delta
            for i in range(1, len(items)):
                prev = items[i-1]["count"]
                curr = items[i]["count"]
                items[i]["delta_pct"] = round((curr - prev) / prev * 100, 1) if prev else 0
            return items
        except Exception as e:
            logger.warning(f"volume_over_time failed: {e}")
            return []

    def _weekday_patterns(self, ts_col: str) -> list[dict]:
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        try:
            res = self.con.execute(f"""
                SELECT
                    DAYOFWEEK(TRY_STRPTIME(CAST("{ts_col}" AS VARCHAR), '%Y-%m-%d %H:%M:%S')) as dow,
                    COUNT(*) as count
                FROM dataset
                WHERE "{ts_col}" IS NOT NULL
                GROUP BY 1
                ORDER BY 1
            """).fetchall()
            if not res or res[0][0] is None:
                res = self.con.execute(f"""
                    SELECT
                        DAYOFWEEK(CAST("{ts_col}" AS TIMESTAMP)) as dow,
                        COUNT(*) as count
                    FROM dataset
                    WHERE "{ts_col}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY 1
                """).fetchall()
            if not res:
                return []

            counts = {r[0]: int(r[1]) for r in res if r[0] is not None}
            total_count = sum(counts.values())
            total_weeks = max(1, total_count // 7)
            mean = total_count / 7 if total_count > 0 else 1

            items = []
            # DuckDB DAYOFWEEK: 0=Sunday, 1=Monday...
            for dow_db in range(0, 7):
                count = counts.get(dow_db, 0)
                dow_mon = (dow_db - 1) % 7  # Convert to Monday=0
                items.append({
                    "weekday": dow_mon,
                    "weekday_name": weekday_names[dow_mon],
                    "count": count,
                    "avg_count_per_week": round(count / total_weeks, 2),
                    "relative_to_mean": round(count / mean, 3) if mean else 0,
                })
            return sorted(items, key=lambda x: x["weekday"])
        except Exception as e:
            logger.warning(f"weekday_patterns failed: {e}")
            return []

    def _hourly_patterns(self, ts_col: str) -> list[dict]:
        try:
            res = self.con.execute(f"""
                SELECT
                    HOUR(TRY_STRPTIME(CAST("{ts_col}" AS VARCHAR), '%Y-%m-%d %H:%M:%S')) as hr,
                    COUNT(*) as count
                FROM dataset
                WHERE "{ts_col}" IS NOT NULL
                GROUP BY 1
                ORDER BY 1
            """).fetchall()
            if not res or res[0][0] is None:
                res = self.con.execute(f"""
                    SELECT HOUR(CAST("{ts_col}" AS TIMESTAMP)) as hr, COUNT(*) as count
                    FROM dataset WHERE "{ts_col}" IS NOT NULL GROUP BY 1 ORDER BY 1
                """).fetchall()
            counts = {r[0]: int(r[1]) for r in res if r[0] is not None}
            total = sum(counts.values())
            mean = total / 24 if total > 0 else 1
            return [
                {
                    "hour": h,
                    "count": counts.get(h, 0),
                    "relative_to_mean": round(counts.get(h, 0) / mean, 3) if mean else 0,
                }
                for h in range(24)
            ]
        except Exception as e:
            logger.warning(f"hourly_patterns failed: {e}")
            return []

    def _duration_minutes(self, start_col: str, end_col: str) -> str:
        return f"""
            (
                DATEDIFF('minute',
                    TRY_STRPTIME(CAST("{start_col}" AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
                    TRY_STRPTIME(CAST("{end_col}" AS VARCHAR), '%Y-%m-%d %H:%M:%S')
                )
            )
        """

    def _duration_metrics(self, start_col: str, end_col: str) -> dict:
        dur = self._duration_minutes(start_col, end_col)
        try:
            res = self.con.execute(f"""
                SELECT
                    AVG({dur}),
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {dur}),
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {dur}),
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {dur}),
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY {dur}),
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY {dur}),
                    STDDEV({dur}),
                    MIN({dur}),
                    MAX({dur}),
                    COUNT(*)
                FROM dataset
                WHERE {dur} > 0 AND {dur} < 525600
            """).fetchone()
            if res and res[0] is not None:
                return {
                    "mean_minutes": round(res[0], 2),
                    "median_minutes": round(res[1], 2),
                    "p25_minutes": round(res[2], 2),
                    "p75_minutes": round(res[3], 2),
                    "p95_minutes": round(res[4], 2),
                    "p99_minutes": round(res[5], 2),
                    "std_dev_minutes": round(res[6] or 0, 2),
                    "min_minutes": round(res[7], 2),
                    "max_minutes": round(res[8], 2),
                    "case_count": int(res[9]),
                }
        except Exception as e:
            logger.warning(f"duration_metrics failed: {e}")
        return {}

    def _category_duration(self, start_col: str, end_col: str, cat_col: Optional[str]) -> list[dict]:
        if not cat_col:
            return []
        dur = self._duration_minutes(start_col, end_col)
        try:
            res = self.con.execute(f"""
                SELECT
                    CAST("{cat_col}" AS VARCHAR) as category,
                    COUNT(*) as count,
                    AVG({dur}) as avg_dur,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {dur}) as median_dur
                FROM dataset
                WHERE {dur} > 0 AND {dur} < 525600 AND "{cat_col}" IS NOT NULL
                GROUP BY 1
                ORDER BY count DESC
                LIMIT 30
            """).fetchall()
            return [
                {
                    "category": str(r[0]),
                    "count": int(r[1]),
                    "avg_duration_minutes": round(r[2], 2) if r[2] else None,
                    "median_duration_minutes": round(r[3], 2) if r[3] else None,
                }
                for r in res
            ]
        except Exception as e:
            logger.warning(f"category_duration failed: {e}")
            return []

    def _top_categories(self, col: str, total: int) -> list[dict]:
        try:
            res = self.con.execute(f"""
                SELECT CAST("{col}" AS VARCHAR) as val, COUNT(*) as cnt
                FROM dataset
                WHERE "{col}" IS NOT NULL
                GROUP BY 1
                ORDER BY cnt DESC
                LIMIT 30
            """).fetchall()
            return [
                {
                    "category": str(r[0]),
                    "count": int(r[1]),
                    "pct": round(int(r[1]) / total * 100, 2) if total else 0,
                }
                for r in res
            ]
        except Exception as e:
            logger.warning(f"top_categories failed for {col}: {e}")
            return []

    def _actor_metrics(
        self, actor_col: str, start_col: Optional[str], end_col: Optional[str],
        sat_col: Optional[str], total: int
    ) -> list[dict]:
        parts = [f'CAST("{actor_col}" AS VARCHAR) as actor', "COUNT(*) as case_count"]
        if start_col and end_col:
            dur = self._duration_minutes(start_col, end_col)
            parts += [
                f"AVG({dur}) as avg_dur",
                f"PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {dur}) as median_dur",
                f"PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY {dur}) as p95_dur",
            ]
        else:
            parts += ["NULL as avg_dur", "NULL as median_dur", "NULL as p95_dur"]

        if sat_col:
            parts.append(f'AVG(TRY_CAST("{sat_col}" AS DOUBLE)) as avg_sat')
        else:
            parts.append("NULL as avg_sat")

        try:
            res = self.con.execute(f"""
                SELECT {', '.join(parts)}
                FROM dataset
                WHERE "{actor_col}" IS NOT NULL
                GROUP BY 1
                ORDER BY case_count DESC
                LIMIT 30
            """).fetchall()
            return [
                {
                    "actor": str(r[0]),
                    "case_count": int(r[1]),
                    "avg_duration_minutes": round(r[2], 2) if r[2] is not None else None,
                    "median_duration_minutes": round(r[3], 2) if r[3] is not None else None,
                    "p95_duration_minutes": round(r[4], 2) if r[4] is not None else None,
                    "avg_satisfaction": round(r[5], 3) if r[5] is not None else None,
                }
                for r in res
            ]
        except Exception as e:
            logger.warning(f"actor_metrics failed for {actor_col}: {e}")
            return []

    def _satisfaction_stats(self, sat_col: str) -> dict:
        try:
            res = self.con.execute(f"""
                SELECT
                    AVG(TRY_CAST("{sat_col}" AS DOUBLE)) as mean,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY TRY_CAST("{sat_col}" AS DOUBLE)) as median,
                    MIN(TRY_CAST("{sat_col}" AS DOUBLE)) as min_val,
                    MAX(TRY_CAST("{sat_col}" AS DOUBLE)) as max_val,
                    STDDEV(TRY_CAST("{sat_col}" AS DOUBLE)) as std,
                    COUNT(*) as total,
                    COUNT(CASE WHEN TRY_CAST("{sat_col}" AS DOUBLE) IS NOT NULL THEN 1 END) as with_score
                FROM dataset
            """).fetchone()
            if res:
                return {
                    "mean": round(res[0], 3) if res[0] else None,
                    "median": round(res[1], 3) if res[1] else None,
                    "min": res[2],
                    "max": res[3],
                    "std_dev": round(res[4], 3) if res[4] else None,
                    "response_rate_pct": round(res[5] / res[5] * 100, 1) if res[5] else 0,
                }
        except Exception as e:
            logger.warning(f"satisfaction_stats failed: {e}")
        return {}

    def _outlier_cases(
        self, case_col: str, start_col: str, end_col: str,
        cat_col: Optional[str], assignee_col: Optional[str]
    ) -> list[dict]:
        dur = self._duration_minutes(start_col, end_col)
        cat_select = f'CAST("{cat_col}" AS VARCHAR)' if cat_col else "NULL"
        asgn_select = f'CAST("{assignee_col}" AS VARCHAR)' if assignee_col else "NULL"
        try:
            res = self.con.execute(f"""
                WITH durations AS (
                    SELECT
                        CAST("{case_col}" AS VARCHAR) as case_id,
                        {dur} as dur_min,
                        {cat_select} as category,
                        {asgn_select} as assignee
                    FROM dataset
                    WHERE {dur} > 0 AND {dur} < 525600
                ),
                stats AS (
                    SELECT AVG(dur_min) as mean, STDDEV(dur_min) as std FROM durations
                )
                SELECT
                    d.case_id, d.dur_min, d.category, d.assignee,
                    (d.dur_min - s.mean) / NULLIF(s.std, 0) as z_score
                FROM durations d, stats s
                WHERE ABS((d.dur_min - s.mean) / NULLIF(s.std, 0)) > 2.5
                ORDER BY ABS(z_score) DESC
                LIMIT 20
            """).fetchall()
            return [
                {
                    "case_id": str(r[0]),
                    "duration_minutes": round(r[1], 2),
                    "category": str(r[2]) if r[2] else None,
                    "assignee": str(r[3]) if r[3] else None,
                    "z_score": round(r[4], 3) if r[4] else 0,
                }
                for r in res
            ]
        except Exception as e:
            logger.warning(f"outlier_cases failed: {e}")
            return []

    def _backlog_aging(self, start_col: str, status_col: Optional[str]) -> list[dict]:
        try:
            # Cases that look "open" based on status, or just all cases with start date
            status_filter = ""
            if status_col:
                status_filter = f"""
                    AND (
                        LOWER(CAST("{status_col}" AS VARCHAR)) IN ('open', 'in progress', 'pending', 'assigned', 'new', 'active', 'waiting')
                        OR "{status_col}" IS NULL
                    )
                """
            res = self.con.execute(f"""
                WITH ages AS (
                    SELECT
                        DATEDIFF('day',
                            TRY_STRPTIME(CAST("{start_col}" AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
                            CURRENT_DATE
                        ) as age_days
                    FROM dataset
                    WHERE "{start_col}" IS NOT NULL {status_filter}
                )
                SELECT
                    CASE
                        WHEN age_days < 1 THEN '< 1 day'
                        WHEN age_days < 7 THEN '1-7 days'
                        WHEN age_days < 30 THEN '8-30 days'
                        WHEN age_days < 90 THEN '31-90 days'
                        WHEN age_days < 180 THEN '91-180 days'
                        ELSE '180+ days'
                    END as bucket,
                    COUNT(*) as count
                FROM ages
                WHERE age_days >= 0
                GROUP BY 1
                ORDER BY MIN(age_days)
            """).fetchall()
            total = sum(r[1] for r in res) or 1
            return [
                {"age_bucket": r[0], "count": int(r[1]), "pct": round(int(r[1]) / total * 100, 2)}
                for r in res
            ]
        except Exception as e:
            logger.warning(f"backlog_aging failed: {e}")
            return []

    def _cross_comparison(
        self, customer_col: str, assignee_col: str,
        start_col: Optional[str], end_col: Optional[str], total: int
    ) -> list[dict]:
        dur = self._duration_minutes(start_col, end_col) if start_col and end_col else "NULL"
        try:
            res = self.con.execute(f"""
                SELECT
                    CAST("{customer_col}" AS VARCHAR) as customer,
                    CAST("{assignee_col}" AS VARCHAR) as assignee,
                    COUNT(*) as count,
                    AVG({dur}) as avg_dur
                FROM dataset
                WHERE "{customer_col}" IS NOT NULL AND "{assignee_col}" IS NOT NULL
                GROUP BY 1, 2
                HAVING COUNT(*) >= 3
                ORDER BY count DESC
                LIMIT 50
            """).fetchall()
            return [
                {
                    "customer": str(r[0]),
                    "assignee": str(r[1]),
                    "count": int(r[2]),
                    "avg_duration_minutes": round(r[3], 2) if r[3] else None,
                }
                for r in res
            ]
        except Exception as e:
            logger.warning(f"cross_comparison failed: {e}")
            return []

    def _reopen_signals(self, case_col: str, status_col: str, total: int) -> dict:
        try:
            res = self.con.execute(f"""
                SELECT
                    COUNT(*) as reopened_count
                FROM dataset
                WHERE LOWER(CAST("{status_col}" AS VARCHAR)) IN ('reopened', 're-opened', 'reopen', 'escalated')
            """).fetchone()
            reopened = res[0] if res else 0
            reopen_rate = round(reopened / total * 100, 2) if total else 0
            return {
                "reopened_count": reopened,
                "reopen_rate_pct": reopen_rate,
                "risk_level": "high" if reopen_rate > 10 else "medium" if reopen_rate > 5 else "low",
            }
        except Exception as e:
            logger.warning(f"reopen_signals failed: {e}")
            return {}

    def _sla_breach_rate(self, sla_col: str, total: int) -> dict:
        try:
            res = self.con.execute(f"""
                SELECT
                    SUM(CASE WHEN LOWER(CAST("{sla_col}" AS VARCHAR)) IN ('true', 'yes', '1', 't', 'y', 'breached') THEN 1 ELSE 0 END) as breached,
                    COUNT(*) as total_with_sla
                FROM dataset
                WHERE "{sla_col}" IS NOT NULL
            """).fetchone()
            if res and res[1]:
                rate = round(res[0] / res[1] * 100, 2)
                return {
                    "breached_count": int(res[0]),
                    "total_with_sla": int(res[1]),
                    "breach_rate_pct": rate,
                    "risk_level": "critical" if rate > 30 else "high" if rate > 15 else "medium" if rate > 5 else "low",
                }
        except Exception as e:
            logger.warning(f"sla_breach_rate failed: {e}")
        return {}
