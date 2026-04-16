# Phase 1 MVP: Upload-Based AI Process Analyzer

## What Phase 1 Delivers

A working end-to-end product slice:

```
CSV Upload → Profiling → Semantic Inference → Column Mapping → Deterministic Analysis → AI Insights
```

### User Journey

1. **Upload** a CSV file (helpdesk export, support tickets, operational log)
2. **View profile**: row count, column types, null ratios, sample values
3. **Review semantic inference**: system guesses what each column means with confidence scores
4. **Confirm/correct mapping**: user validates case ID, timestamps, assignee, category, satisfaction columns
5. **Run analysis**: deterministic metrics computed in seconds
6. **View insights**: ranked, evidence-backed findings with recommended actions
7. **Read AI summary**: LLM narrative grounded in the computed evidence
8. **Export**: full JSON export of dataset + results

### What the System Can Tell You

Given a typical ITSM or support dataset, the system produces findings like:

> "Password Reset accounts for 25.1% of all cases (1,254 records) — the most dominant category. 
> This concentration suggests a systematic, recurring issue addressable at root cause."
> Support: 1,254 | Effect: 0.25 | Confidence: 85%

> "Monday accounts for 2.1x the daily average volume. This pattern suggests systematic demand 
> drivers — likely post-weekend access issues and forgotten passwords."
> Support: 450 cases | Effect: 1.1 | Confidence: 83%

> "Assignee 'carol.slow' handles 600 cases with a median resolution of 480 min — 2.8 standard 
> deviations above the group average of 175 min."
> Support: 600 | Effect: 0.93 | Confidence: 72%

These are not LLM hallucinations. They are programmatic detections, surfaced to the LLM as evidence.

---

## Scope Boundaries

### In Scope (Phase 1)

- ✅ CSV upload (up to 500MB, 1M+ rows)
- ✅ Streaming Parquet conversion
- ✅ Full schema profiling (25+ metrics per column)
- ✅ 25 semantic role inference with confidence
- ✅ Process readiness scoring
- ✅ User mapping review/correction
- ✅ 12 insight families, programmatically detected
- ✅ Insight ranking by evidence strength
- ✅ LLM evidence pack + commentary (OpenAI or mock)
- ✅ Web UI: upload, profile, mapping, results dashboard
- ✅ JSON export
- ✅ Job history
- ✅ Docker Compose local deployment
- ✅ CI pipeline
- ✅ Demo datasets with known patterns

### Out of Scope (Phase 1)

- ❌ Authentication / multi-user
- ❌ XLSX, JSON, XML formats (CSV only)
- ❌ Connector-based ingestion (ServiceNow, Jira, etc.)
- ❌ Real-time streaming data
- ❌ Process discovery (DFG, Petri nets)
- ❌ Conformance checking
- ❌ S3/MinIO storage (local FS only)
- ❌ Alerting / scheduled runs
- ❌ Custom insight rules

---

## Known Limitations & Tradeoffs

| Limitation | Decision |
|-----------|----------|
| No auth | Phase 1 is a single-user local tool. Auth added in Phase 2. |
| TypeORM `synchronize: true` | Acceptable for MVP. Replace with Alembic/migrations before multi-tenant. |
| In-memory file upload (multer) | Max 600MB in memory. For larger files, switch to stream-to-disk. |
| Approx distinct counts | `approx_count_distinct` may have ±2% error for very high cardinality. Acceptable for profiling. |
| Semantic inference is rule-based | ML-based inference (fine-tuned model) is a Phase 2+ enhancement. |
| LLM mock commentary | Plausible but not as rich as GPT-4. Configure `OPENAI_API_KEY` for production quality. |
| No chunked CSV for Polars | Polars `scan_csv` + `collect()` is lazy but collects in memory. Switch to chunked processing for 2GB+ files. |

---

## Insight Engine Design Notes

### Why Programmatic Before LLM?

The LLM has no context about your specific data. It cannot:
- Know that 2.1x Monday volume is significant for your organization
- Identify that a specific assignee's 480-min median is 2.8 standard deviations above the group
- Detect that 25% of tickets are in one category

These require SQL queries over real data. The LLM's role is to interpret these findings in natural language and hypothesize root causes — not to discover them.

### Insight Confidence Scoring

Each insight candidate has a `confidence` field (0.0-1.0) derived from:
- Statistical significance (support count relative to total)
- Effect size (how large the observed difference is)
- Variance of the baseline metric
- Data quality signals from profiling

Low-confidence insights (<0.50) are ranked lower and the UI shows uncertainty explicitly.

### Effect Size Normalization

Different insight types use different effect size measures:
- **Temporal spike**: ratio to daily mean - 1.0 (e.g., 2.1x → effect 1.1)
- **Performance gap**: normalized Z-score / 3.0 (keeps 0-1 range for 3-sigma events)
- **Customer delay**: ratio to customer group average - 1.0
- **Satisfaction degradation**: 1.0 - (mean/max) (e.g., 3.5/5 → 0.30)

---

## Future Evolution (Phase 2+)

This Phase 1 system is designed to evolve toward a full process mining platform:

### Architecture Evolution Path

```
Phase 1: CSV Upload → Evidence Engine → LLM Commentary
         ↓
Phase 2: Connector Ingestion → Structured Event Logs → Evidence Engine → LLM Commentary
         ↓
Phase 3: + Process Discovery (DFG) + Conformance Checking + Process Intelligence
         ↓
Phase 4: + Multi-tenant + Connectors + Real-time + Custom Rules + Alerts
```

### Database Schema Evolution

The JSONB columns (`profiling_result`, `metrics_result`, `insight_candidates`) store rich structured data today. In Phase 2, these can be normalized into dedicated tables:
- `column_profiles` table (one row per column)
- `semantic_inferences` table
- `metrics` table (typed rows per metric)
- `insight_candidates` table (indexed, searchable)

The `datasets` table already has `metadata JSONB`-style extensibility via the full result payload.

### Storage Evolution

`StorageService` in the API abstracts file paths. To switch to S3:
1. Replace `StorageService` implementation with S3 SDK calls
2. Update Docker Compose to add MinIO container (or configure AWS credentials)
3. No changes needed in controllers, services, or worker

### Connector Evolution

The analysis worker is already designed as a stateless processing service. In Phase 2:
1. Add `connectors/` directory to the worker
2. Each connector produces a normalized event log (same Parquet schema)
3. The rest of the pipeline (profiling → metrics → insights → LLM) runs unchanged
