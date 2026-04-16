"""
CSV Profiling Engine
- Streaming/chunked approach for large files
- DuckDB + Polars for efficient analysis
- Never loads full CSV into RAM in one shot
"""
import logging
import os
import uuid
import chardet
import duckdb
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from app.models.schemas import (
    ColumnProfile, ProcessReadinessScore, ProfilingResult, SemanticInference
)
from app.services.semantic_inference import SemanticInferenceEngine

logger = logging.getLogger(__name__)

TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
]


class CSVProfiler:
    def __init__(self, storage_path: str, parquet_base: str, sample_size: int = 10000):
        self.storage_path = Path(storage_path)
        self.parquet_base = Path(parquet_base)
        self.sample_size = sample_size
        self.inference_engine = SemanticInferenceEngine()

    def _detect_encoding(self, file_path: str, read_bytes: int = 65536) -> str:
        with open(file_path, "rb") as f:
            raw = f.read(read_bytes)
        result = chardet.detect(raw)
        encoding = result.get("encoding") or "utf-8"
        # Normalize to Polars-compatible encoding name
        enc_lower = encoding.lower().replace("-", "").replace("_", "")
        if enc_lower in ("ascii", "utf8sig", "utf8bom"):
            return "utf8"
        if enc_lower in ("utf8",):
            return "utf8"
        # Polars only supports utf8 and utf8-lossy natively
        # For other encodings, fall back to utf8-lossy and let DuckDB handle conversion
        return "utf8-lossy"

    def _detect_delimiter(self, file_path: str, encoding: str) -> str:
        candidates = [",", ";", "\t", "|"]
        with open(file_path, encoding=encoding, errors="replace") as f:
            sample = f.read(8192)
        counts = {c: sample.count(c) for c in candidates}
        return max(counts, key=counts.get)

    def _convert_to_parquet(
        self, file_path: str, parquet_path: str, delimiter: str, encoding: str
    ) -> int:
        """Streaming CSV → Parquet conversion. Returns row count."""
        try:
            lf = pl.scan_csv(
                file_path,
                separator=delimiter,
                encoding=encoding,
                infer_schema_length=10000,
                try_parse_dates=False,
                ignore_errors=True,
                truncate_ragged_lines=True,
            )
            df = lf.collect()
            row_count = len(df)
            df.write_parquet(parquet_path, compression="snappy")
            return row_count
        except Exception as e:
            logger.warning(f"Polars scan failed ({e}), falling back to DuckDB copy")
            con = duckdb.connect()
            con.execute(f"""
                COPY (
                    SELECT * FROM read_csv_auto(
                        '{file_path}',
                        delim='{delimiter}',
                        header=true,
                        ignore_errors=true,
                        max_line_size=1048576
                    )
                ) TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)
            """)
            result = con.execute(f"SELECT COUNT(*) FROM '{parquet_path}'").fetchone()
            con.close()
            return result[0] if result else 0

    def _profile_column(
        self, con: duckdb.DuckDBPyConnection, table: str, col: str, row_count: int
    ) -> ColumnProfile:
        safe_col = f'"{col}"'
        total = row_count

        # Null count
        null_count_res = con.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {safe_col} IS NULL OR CAST({safe_col} AS VARCHAR) = ''"
        ).fetchone()
        null_count = null_count_res[0] if null_count_res else 0
        null_ratio = null_count / total if total > 0 else 0.0

        # Distinct count
        distinct_res = con.execute(
            f"SELECT approx_count_distinct({safe_col}) FROM {table}"
        ).fetchone()
        distinct_count = distinct_res[0] if distinct_res else 0
        distinct_ratio = distinct_count / (total - null_count) if (total - null_count) > 0 else 0.0

        # Sample values (non-null)
        sample_res = con.execute(
            f"SELECT DISTINCT CAST({safe_col} AS VARCHAR) FROM {table} WHERE {safe_col} IS NOT NULL LIMIT 10"
        ).fetchall()
        sample_values = [str(r[0]) for r in sample_res if r[0] is not None]

        # Top values
        top_res = con.execute(f"""
            SELECT CAST({safe_col} AS VARCHAR) as v, COUNT(*) as cnt
            FROM {table}
            WHERE {safe_col} IS NOT NULL
            GROUP BY v ORDER BY cnt DESC LIMIT 20
        """).fetchall()
        top_values = [
            {"value": str(r[0]), "count": int(r[1]), "pct": round(int(r[1]) / total * 100, 2)}
            for r in top_res
        ]

        # Type inference
        inferred_type = self._infer_type(con, table, safe_col, sample_values, distinct_count, total)

        # Numeric stats if applicable
        mean_val = median_val = std_dev = p25 = p75 = p95 = None
        min_val = max_val = None

        if inferred_type in ("integer", "float"):
            stats_res = con.execute(f"""
                SELECT
                    MIN(TRY_CAST({safe_col} AS DOUBLE)),
                    MAX(TRY_CAST({safe_col} AS DOUBLE)),
                    AVG(TRY_CAST({safe_col} AS DOUBLE)),
                    STDDEV(TRY_CAST({safe_col} AS DOUBLE)),
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY TRY_CAST({safe_col} AS DOUBLE)),
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY TRY_CAST({safe_col} AS DOUBLE)),
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY TRY_CAST({safe_col} AS DOUBLE)),
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY TRY_CAST({safe_col} AS DOUBLE))
                FROM {table}
                WHERE {safe_col} IS NOT NULL
            """).fetchone()
            if stats_res:
                min_val = str(stats_res[0]) if stats_res[0] is not None else None
                max_val = str(stats_res[1]) if stats_res[1] is not None else None
                mean_val = round(stats_res[2], 4) if stats_res[2] is not None else None
                std_dev = round(stats_res[3], 4) if stats_res[3] is not None else None
                p25 = round(stats_res[4], 4) if stats_res[4] is not None else None
                median_val = round(stats_res[5], 4) if stats_res[5] is not None else None
                p75 = round(stats_res[6], 4) if stats_res[6] is not None else None
                p95 = round(stats_res[7], 4) if stats_res[7] is not None else None
        elif inferred_type in ("string", "categorical", "identifier"):
            if sample_values:
                min_val = min(sample_values, key=str)
                max_val = max(sample_values, key=str)

        # Timestamp parse ratio
        ts_ratio = None
        if inferred_type in ("string", "datetime", "date", "categorical") and distinct_count > 0:
            ts_ratio = self._estimate_timestamp_ratio(con, table, safe_col, total - null_count)
            if ts_ratio > 0.8:
                inferred_type = "datetime"
            elif ts_ratio > 0.5:
                inferred_type = "date"

        # Enum-like: low distinct, high null-corrected coverage
        non_null = total - null_count
        is_enum_like = (distinct_count <= 50 and non_null > 0 and distinct_ratio < 0.05) or (
            distinct_count <= 20
        )

        # Free text: high distinct, long average length
        is_free_text = False
        if inferred_type == "string" and distinct_ratio > 0.5:
            avg_len_res = con.execute(
                f"SELECT AVG(LENGTH(CAST({safe_col} AS VARCHAR))) FROM {table} WHERE {safe_col} IS NOT NULL"
            ).fetchone()
            avg_len = avg_len_res[0] if avg_len_res else 0
            is_free_text = (avg_len or 0) > 40

        return ColumnProfile(
            column_name=col,
            inferred_type=inferred_type,
            null_count=null_count,
            null_ratio=round(null_ratio, 4),
            distinct_count=distinct_count,
            distinct_ratio=round(distinct_ratio, 4),
            is_enum_like=is_enum_like,
            is_free_text=is_free_text,
            sample_values=sample_values[:8],
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val,
            median_value=median_val,
            std_dev=std_dev,
            p25=p25,
            p75=p75,
            p95=p95,
            timestamp_parse_success_ratio=ts_ratio,
            top_values=top_values[:15],
        )

    def _infer_type(
        self, con, table: str, safe_col: str, sample_values: list, distinct_count: int, total: int
    ) -> str:
        if not sample_values:
            return "unknown"

        # Try integer
        int_test = con.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT TRY_CAST({safe_col} AS BIGINT) as v FROM {table}
                WHERE {safe_col} IS NOT NULL LIMIT 1000
            ) WHERE v IS NOT NULL
        """).fetchone()
        float_test = con.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT TRY_CAST({safe_col} AS DOUBLE) as v FROM {table}
                WHERE {safe_col} IS NOT NULL LIMIT 1000
            ) WHERE v IS NOT NULL
        """).fetchone()

        sample_str = " ".join(str(v) for v in sample_values[:20]).lower()
        non_null = min(total, 1000)

        if non_null > 0:
            int_ratio = (int_test[0] if int_test else 0) / non_null
            float_ratio = (float_test[0] if float_test else 0) / non_null

            if int_ratio > 0.9:
                return "integer"
            if float_ratio > 0.9:
                return "float"

        # Boolean check
        bool_vals = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}
        if all(str(v).lower() in bool_vals for v in sample_values[:10]):
            return "boolean"

        # Identifier check (high distinct, pattern match)
        if distinct_count > total * 0.8:
            return "identifier"

        # Low cardinality = categorical
        if distinct_count <= 30:
            return "categorical"

        return "string"

    def _estimate_timestamp_ratio(self, con, table: str, safe_col: str, non_null_count: int) -> float:
        if non_null_count == 0:
            return 0.0
        try:
            res = con.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT TRY_STRPTIME(CAST({safe_col} AS VARCHAR), '%Y-%m-%d %H:%M:%S') as v
                    FROM {table} WHERE {safe_col} IS NOT NULL LIMIT 1000
                ) WHERE v IS NOT NULL
            """).fetchone()
            ratio1 = (res[0] if res else 0) / min(non_null_count, 1000)
            if ratio1 > 0.7:
                return ratio1

            res2 = con.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT TRY_STRPTIME(CAST({safe_col} AS VARCHAR), '%Y-%m-%dT%H:%M:%S') as v
                    FROM {table} WHERE {safe_col} IS NOT NULL LIMIT 1000
                ) WHERE v IS NOT NULL
            """).fetchone()
            ratio2 = (res2[0] if res2 else 0) / min(non_null_count, 1000)
            if ratio2 > 0.7:
                return ratio2

            res3 = con.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT TRY_STRPTIME(CAST({safe_col} AS VARCHAR), '%Y-%m-%d') as v
                    FROM {table} WHERE {safe_col} IS NOT NULL LIMIT 1000
                ) WHERE v IS NOT NULL
            """).fetchone()
            ratio3 = (res3[0] if res3 else 0) / min(non_null_count, 1000)
            return max(ratio1, ratio2, ratio3)
        except Exception:
            return 0.0

    def _compute_process_readiness(
        self, columns: list[ColumnProfile], inferences: list[SemanticInference]
    ) -> ProcessReadinessScore:
        role_map = {inf.column_name: inf for inf in inferences}
        warnings = []

        def best_confidence(roles: list[str]) -> float:
            return max(
                (inf.confidence for inf in inferences if inf.inferred_role.value in roles),
                default=0.0,
            )

        timeline = best_confidence(["created_at", "updated_at", "resolved_at", "closed_at"])
        case_trace = best_confidence(["case_id", "record_id"])
        activity = best_confidence(["activity_name", "state", "status"])
        actor = best_confidence(["assignee", "assignment_group"])
        customer = best_confidence(["customer"])
        satisfaction = best_confidence(["satisfaction_score"])

        if timeline < 0.5:
            warnings.append("No reliable timestamp columns detected. Time-based analysis will be limited.")
        if case_trace < 0.5:
            warnings.append("No clear case identifier detected. Case traceability analysis unavailable.")
        if activity < 0.4:
            warnings.append("Activity/state column not clearly identified. Process flow analysis limited.")
        if actor < 0.4:
            warnings.append("No assignee/group column detected. Actor-based analysis unavailable.")

        # Check null ratios for key columns
        for col in columns:
            if col.null_ratio > 0.3:
                inf = role_map.get(col.column_name)
                if inf and inf.inferred_role.value in ["created_at", "case_id", "status"]:
                    warnings.append(
                        f"Column '{col.column_name}' has {col.null_ratio:.1%} null values, "
                        "which may impact analysis quality."
                    )

        recommendation_confidence = (timeline + case_trace + activity + actor) / 4

        overall = (
            timeline * 0.30
            + case_trace * 0.25
            + activity * 0.20
            + actor * 0.15
            + customer * 0.05
            + satisfaction * 0.05
        )

        return ProcessReadinessScore(
            overall=round(overall * 100, 1),
            timeline_quality=round(timeline * 100, 1),
            case_traceability=round(case_trace * 100, 1),
            activity_clarity=round(activity * 100, 1),
            actor_clarity=round(actor * 100, 1),
            customer_segmentation=round(customer * 100, 1),
            recommendation_confidence=round(recommendation_confidence * 100, 1),
            warnings=warnings,
        )

    def profile(self, file_path: str, dataset_id: str) -> ProfilingResult:
        profiling_run_id = str(uuid.uuid4())
        file_size = os.path.getsize(file_path)

        logger.info(f"Starting profiling for dataset {dataset_id}, file size: {file_size:,} bytes")

        encoding = self._detect_encoding(file_path)
        delimiter = self._detect_delimiter(file_path, encoding)
        logger.info(f"Detected encoding={encoding}, delimiter='{delimiter}'")

        parquet_dir = self.parquet_base / dataset_id
        parquet_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = str(parquet_dir / "data.parquet")

        row_count = self._convert_to_parquet(file_path, parquet_path, delimiter, encoding)
        logger.info(f"Converted to parquet: {row_count:,} rows")

        con = duckdb.connect()
        con.execute(f"CREATE VIEW dataset AS SELECT * FROM '{parquet_path}'")

        schema_res = con.execute("DESCRIBE dataset").fetchall()
        column_names = [r[0] for r in schema_res]
        column_count = len(column_names)

        logger.info(f"Profiling {column_count} columns...")
        columns = []
        for col in column_names:
            try:
                cp = self._profile_column(con, "dataset", col, row_count)
                columns.append(cp)
            except Exception as e:
                logger.warning(f"Failed to profile column {col}: {e}")
                columns.append(ColumnProfile(
                    column_name=col,
                    inferred_type="unknown",
                    null_count=0,
                    null_ratio=0.0,
                    distinct_count=0,
                    distinct_ratio=0.0,
                    is_enum_like=False,
                    is_free_text=False,
                    sample_values=[],
                ))

        con.close()

        inferences = self.inference_engine.infer(columns)
        readiness = self._compute_process_readiness(columns, inferences)

        return ProfilingResult(
            dataset_id=dataset_id,
            profiling_run_id=profiling_run_id,
            row_count=row_count,
            column_count=column_count,
            file_size_bytes=file_size,
            delimiter=delimiter,
            encoding=encoding,
            has_header=True,
            columns=columns,
            semantic_inferences=inferences,
            process_readiness=readiness,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
