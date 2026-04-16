# Architecture: ProcessMiner Phase 1

## Design Principles

1. **Evidence-First**: All insights are generated programmatically before LLM is called
2. **LLM as Commentator**: LLM receives only a structured evidence pack; never raw data
3. **Determinism**: Same data → same metrics, always
4. **Streaming Scale**: Large files never fully loaded into RAM
5. **Storage Abstraction**: Local filesystem now; S3/MinIO-compatible later
6. **Separation of Concerns**: Analysis engine decoupled from API and UI

---

## Component Architecture

### apps/web (React + Vite)

**Responsibilities**: User interface only. No business logic.

Key pages:
- `UploadPage`: File selection + upload with progress
- `DatasetsPage`: Dataset list with status
- `DatasetDetailPage`: 4-tab detail (Overview, Profile, Mapping, Results)
- `AnalysisResultsPage`: Full results dashboard (Insights, AI Summary, Metrics, Recommendations)
- `JobsPage`: Background job history

State management: Custom hooks (`useDataset`, `useDatasets`) with polling for active jobs.

### apps/api (NestJS)

**Responsibilities**: HTTP interface, file storage, job orchestration, state machine, database persistence.

Key patterns:
- **Dataset State Machine**: `uploaded → profiling → awaiting-mapping → analyzing → completed | failed`
- **Fire-and-forget**: Triggers Python worker via HTTP, registers job; callback from worker via `/internal/jobs/:id/complete`
- **Storage Abstraction**: `StorageService` handles file paths; swap implementation for S3

Modules:
- `DatasetsModule`: Upload, profile, mapping, analyze
- `JobsModule`: Job history
- `InternalModule`: Worker callback endpoints

### services/analysis-worker (Python + FastAPI)

**Responsibilities**: All analysis logic. Completely stateless between requests.

Pipeline stages:

```
1. CSV Sniffing (chardet + delimiter detection)
2. Parquet Conversion (Polars lazy scan → write_parquet)
3. Column Profiling (DuckDB SQL queries)
4. Semantic Inference (rule-based pattern matching)
5. Process Readiness Scoring
6. Deterministic Metrics (DuckDB aggregations)
7. Insight Candidate Generation (programmatic detection)
8. Evidence Pack Assembly
9. LLM Commentary (OpenAI or mock)
```

---

## Data Flow

### Upload Flow

```
Browser → POST /datasets/upload (multipart)
        → API stores file to /data/storage/{dataset_id}/{filename}
        → Creates DatasetEntity (status: uploaded)
        → Returns dataset_id

Browser → POST /datasets/:id/profile
        → API creates JobRunEntity (type: profiling)
        → API calls Worker: POST /profiling/run (async)
        → Returns immediately with job_id

Worker  → Reads CSV from storage path
        → Converts to Parquet at /data/parquet/{dataset_id}/data.parquet
        → Profiles all columns via DuckDB
        → Runs semantic inference
        → Computes process readiness score
        → POSTs to API: POST /internal/jobs/:job_id/complete (with result payload)

API     → Updates DatasetEntity:
          status → awaiting-mapping
          row_count, column_count
          profiling_result (full JSON)
```

### Analysis Flow

```
Browser → POST /datasets/:id/mapping (column mapping JSON)
        → API updates mappingDecision on DatasetEntity
        → Status remains awaiting-mapping

Browser → POST /datasets/:id/analyze
        → API creates AnalysisRunEntity + JobRunEntity
        → Status → analyzing
        → API calls Worker: POST /analysis/run (async)

Worker  → Reads Parquet from /data/parquet/{dataset_id}/data.parquet
        → Runs MetricsEngine (DuckDB SQL, no Python loops over rows)
        → Runs InsightCandidateEngine (Python, operates on aggregated metrics)
        → Assembles EvidencePack (JSON, ~5-50KB, never raw rows)
        → Calls LLMService.generate_commentary(evidence_pack)
        → POSTs results to /internal/jobs/:id/complete

API     → Stores results in AnalysisRunEntity
        → Updates DatasetEntity: status → completed
```

---

## Profiling Engine

### CSV to Parquet

```python
# Polars lazy scan (streaming, low RAM)
lf = pl.scan_csv(file_path, separator=delimiter, infer_schema_length=10000)
df = lf.collect()
df.write_parquet(path, compression='snappy')

# Fallback: DuckDB COPY for edge cases
COPY (SELECT * FROM read_csv_auto(...)) TO '...' (FORMAT PARQUET)
```

### Column Profiling (DuckDB)

Each column is profiled via targeted SQL queries:
- `approx_count_distinct()` for high-cardinality columns
- `TRY_CAST` for type validation
- `PERCENTILE_CONT` for numeric stats
- `TRY_STRPTIME` for timestamp detection

### Semantic Inference

Pattern matching system with 3 layers:

1. **Name patterns** (regex, 50+ patterns): `opened_at → created_at` (0.95 confidence)
2. **Type signals**: datetime type boosts timestamp roles; identifier type boosts ID roles
3. **Value signals**: Status vocabulary overlap, priority vocab, channel vocab, scale ranges

Role penalization: If a role is already assigned to another column with high confidence, subsequent matches are penalized.

---

## Insight Engine

### Detection Logic

Each insight family operates on pre-aggregated metrics (not raw rows):

```python
# Example: Weekday spike detection
for weekday in weekday_patterns:
    if weekday.relative_to_mean > 1.4:  # 40% above mean
        effect = ratio - 1.0
        confidence = min(0.90, 0.55 + effect * 0.30)
        yield InsightCandidate(...)
```

### Ranking Formula

```
rank_score = log(support_count) × effect_size × confidence × actionability_weight
```

Actionability weights by type (0.50-0.90):
- `satisfaction_degradation`: 0.90 (highest — customer impact)
- `queue_bottleneck`: 0.85
- `workload_imbalance`: 0.85
- `self_service_opportunity`: 0.85
- `assignee_performance_gap`: 0.80

Top 15 candidates ranked and passed to LLM.

---

## LLM Layer

### Provider Abstraction

```python
class LLMProvider(ABC):
    @abstractmethod
    def generate_commentary(self, evidence_pack: dict) -> dict:
        pass

class OpenAIProvider(LLMProvider): ...
class MockLLMProvider(LLMProvider): ...

class LLMService:
    def _get_provider(self):
        if OPENAI_API_KEY and not USE_MOCK_LLM:
            return OpenAIProvider()
        return MockLLMProvider()
```

### Evidence Pack Structure (~5-50KB)

```json
{
  "dataset_summary": { "row_count": 5000, "date_range": "...", ... },
  "mapping_decisions": { "created_at_column": "opened_at", ... },
  "metric_summary": {
    "duration_metrics": { "median_minutes": 240, "p95_minutes": 2880, ... },
    "weekday_patterns": [...],
    "top_categories": [...],
    "top_assignees": [...],
    ...
  },
  "ranked_insights": [
    {
      "insight_type": "temporal_spike",
      "title": "Volume Spike on Mondays",
      "support_count": 450,
      "effect_size": 1.1,
      "confidence": 0.83,
      "evidence_refs": { "weekday": "Monday", "ratio": 2.1 },
      "recommended_action_seed": "..."
    },
    ...
  ]
}
```

### System Prompt Design

The system prompt enforces:
1. No invented metrics
2. All claims reference specific evidence
3. State uncertainty explicitly when confidence is low
4. Professional, management-audience tone

---

## Database Schema

| Table | Description |
|-------|-------------|
| `datasets` | Dataset metadata, status, paths, profiling/mapping/analysis results (JSONB) |
| `analysis_runs` | Each analysis run with mapping snapshot and results (JSONB) |
| `job_runs` | Background job tracking (profiling/analysis) |

JSONB columns allow storing rich nested results without separate tables, enabling Phase 2 schema evolution without migrations.

---

## Storage

### Current: Local Filesystem

```
/data/
  storage/          ← uploaded CSV files
    {dataset_id}/
      original.csv
  parquet/          ← converted Parquet files
    {dataset_id}/
      data.parquet
  artifacts/        ← future: exported reports, charts
```

### Future: S3-Compatible

`StorageService` in the API is the single abstraction point. Replace the local file operations with `@aws-sdk/client-s3` or MinIO client — no changes needed elsewhere.

---

## Scale Characteristics

### Memory Usage During Profiling

| Step | Memory |
|------|--------|
| CSV read (Polars lazy) | O(chunk_size) not O(file_size) |
| Parquet write | Streaming |
| DuckDB profiling | DuckDB manages its own buffer pool |
| Insight generation | O(aggregated_metrics) ≈ <1MB |
| Evidence pack | ~5-50KB |
| LLM call | HTTP only; no data in memory |

### Throughput Estimates (local SSD)

| File Size | Rows | Profiling Time |
|-----------|------|----------------|
| 50MB | 100k | ~5s |
| 200MB | 500k | ~20s |
| 500MB | 1M | ~60s |

---

## Security Notes

- No authentication in Phase 1 (single-user local tool)
- File type validation: only `.csv` and `.csv.gz` accepted
- File size limit enforced at API level
- No SQL injection risk: DuckDB queries use parameterized file paths
- LLM API key stored as environment variable, never in database
