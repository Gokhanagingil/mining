# ProcessMiner — AI Process Analyzer

> **Phase 1 MVP**: Upload-based process mining with evidence-first AI insights

ProcessMiner transforms raw process data (CSV exports from ServiceNow, Jira, Zendesk, etc.) into structured, evidence-backed operational intelligence. It combines deterministic analysis with carefully grounded LLM commentary — never generating metrics from thin air.

## Core Philosophy

```
Upload → Profiling → Semantic Inference → Quality Gate
       → Deterministic Metrics → Evidence Pack → LLM Commentary
```

**The LLM never sees your raw data. It only sees the evidence pack.**

---

## Quick Start (Docker)

```bash
# 1. Clone and configure
cp .env.example .env
# Optionally add your OpenAI key for richer AI commentary:
# OPENAI_API_KEY=sk-...

# 2. Start everything
cd infra
docker compose up --build

# 3. Open the UI
open http://localhost:5173
```

Services:
| Service | URL | Description |
|---------|-----|-------------|
| Web UI | http://localhost:5173 | React frontend |
| API | http://localhost:3001 | NestJS REST API |
| Worker | http://localhost:8000 | Python analysis engine |
| Postgres | localhost:5432 | Database |

---

## Demo Datasets

Two ready-to-use demo CSV files are in `datasets/`:

### 1. `password-reset-spike.csv` (5,000 rows)
IT helpdesk dataset with a strong Monday morning pattern for password resets.

**Insights you'll see:**
- 📈 Volume Spike on Mondays (2.1x daily average)
- 🤖 Self-Service Opportunity: "Password Reset" (25% of all tickets)
- 🔍 Assignee performance gaps (james.harris, robert.lewis are 2x slower)
- 😟 Below-target satisfaction for slow assignees
- ↩️ Case reopen signals

### 2. `customer-assignee-performance.csv` (4,000 rows)
Customer support dataset with deliberate assignee performance gaps and customer-specific delay patterns.

**Insights you'll see:**
- 🔍 Performance gap: thomas.berg (1.6x slower, lower satisfaction)
- 👤 Customer-specific delays: "Acme Corp", "MedGroup" cases take longer
- 🚧 Queue bottleneck: Integration Team P95 latency
- 😟 Satisfaction degradation for specific assignees

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        apps/web                              │
│              React + Vite + TypeScript + Tailwind            │
│        Upload → Profile → Map → Analyze → Dashboard         │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                        apps/api                              │
│              NestJS + TypeScript + TypeORM                   │
│    Upload handler · Job orchestrator · State machine         │
└────────────┬────────────────────────┬───────────────────────┘
             │ PostgreSQL             │ HTTP (internal)
             │                        │
┌────────────▼──┐        ┌────────────▼────────────────────────┐
│  PostgreSQL   │        │    services/analysis-worker          │
│  · datasets   │        │    FastAPI + DuckDB + Polars         │
│  · job_runs   │        │                                      │
│  · analysis_  │        │    ┌──────────────────────────┐     │
│    runs       │        │    │ CSV Profiler              │     │
│  · profiling  │        │    │ Semantic Inference Engine │     │
│    results    │        │    │ Metrics Engine (DuckDB)   │     │
└───────────────┘        │    │ Insight Candidate Engine  │     │
                         │    │ LLM Commentary Layer      │     │
                         │    └──────────────────────────┘     │
                         └─────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for detailed design.

---

## Features

### Dataset Upload
- CSV files up to 500MB (1M+ rows)
- Upload progress tracking
- Streaming conversion to Parquet format
- Never loads full file into RAM

### Schema Profiling
- Delimiter and encoding detection
- Type inference (string, integer, float, datetime, categorical, identifier)
- Null ratio, distinct count, sample values
- Timestamp parse success ratio
- Free-text vs enum-like detection

### Semantic Column Inference
Automatic role detection for ~25 semantic roles:
- `case_id`, `activity_name`, `status`, `created_at`, `resolved_at`
- `assignee`, `assignment_group`, `customer`, `category`, `priority`
- `satisfaction_score`, `sla_breach_flag`, `duration`, `channel`...

Each inference includes: confidence, reason, sample justification, alternatives.

### Process Readiness Score
6-dimensional quality score (0-100):
- Timeline Quality, Case Traceability, Activity Clarity
- Actor Clarity, Customer Segmentation, Recommendation Confidence

### Column Mapping Review
- User confirms or corrects semantic assignments
- Auto-fill from inference suggestions
- Saved per dataset, supports re-run

### Deterministic Metrics Engine
All metrics computed via DuckDB SQL over Parquet:
- Volume over time (monthly)
- Weekday/hourly patterns
- Duration percentiles (P25, P50, P75, P95, P99)
- Top categories, assignees, groups, customers
- Backlog aging buckets
- Reopen/loop signals
- Cross-tabulation: customer × assignee performance
- Outlier case detection (Z-score)

### Insight Candidate Engine (Programmatic)
12 insight families, ranked by `log(support) × effect_size × confidence × actionability`:
1. Temporal Spike
2. Workload Imbalance
3. Customer-Specific Delay
4. Assignee Performance Gap
5. Category Recurrence / High Duration
6. Satisfaction Degradation
7. Self-Service Opportunity
8. Routing Problem
9. Queue Bottleneck
10. Rework/Loop Pattern
11. Backlog Aging
12. Outlier Cases

### LLM Commentary (Evidence-Grounded)
- Provider abstraction (OpenAI GPT-4o adapter + mock fallback)
- Mock provider produces plausible, evidence-grounded commentary without API call
- Evidence pack sent to LLM: never raw CSV data
- Output: executive summary, process manager findings, bottlenecks, hypotheses, recommendations

### Results Dashboard
- Insight cards with expandable evidence panels
- Volume/weekday charts (Recharts)
- Category/assignee breakdowns
- AI summary with confidence indicators
- Prioritized recommendations with effort estimation

---

## Development

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### Local Development (without Docker)

```bash
# 1. Start Postgres
docker run -d --name postgres \
  -e POSTGRES_DB=mining -e POSTGRES_USER=mining -e POSTGRES_PASSWORD=mining \
  -p 5432:5432 postgres:16-alpine

# 2. Start analysis worker
cd services/analysis-worker
pip install -r requirements.txt
WORKER_STORAGE_PATH=/tmp/storage WORKER_PARQUET_PATH=/tmp/parquet \
WORKER_DATABASE_URL=postgresql://mining:mining@localhost:5432/mining \
uvicorn app.main:app --port 8000 --reload

# 3. Start API
cd apps/api
npm install
DATABASE_URL=postgresql://mining:mining@localhost:5432/mining \
WORKER_URL=http://localhost:8000 \
npm run start:dev

# 4. Start web
cd apps/web
npm install
VITE_API_URL=http://localhost:3001 npm run dev
```

### Running Tests

```bash
# Python tests
cd services/analysis-worker
PYTHONPATH=. WORKER_STORAGE_PATH=/tmp/storage WORKER_PARQUET_PATH=/tmp/parquet \
WORKER_DATABASE_URL="" WORKER_USE_MOCK_LLM=true \
pytest tests/ -v

# API tests
cd apps/api
npm test

# Frontend build check
cd apps/web
npm run build
```

### Generating Demo Datasets

```bash
cd datasets
python3 generate_datasets.py
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/datasets/upload` | Upload CSV file |
| GET | `/datasets` | List all datasets |
| GET | `/datasets/:id` | Get dataset details |
| POST | `/datasets/:id/profile` | Start profiling job |
| GET | `/datasets/:id/profile` | Get profiling results |
| POST | `/datasets/:id/mapping` | Save column mapping |
| POST | `/datasets/:id/analyze` | Start analysis run |
| GET | `/datasets/:id/results` | Get latest analysis results |
| GET | `/datasets/:id/insights` | Get insight candidates |
| GET | `/datasets/:id/runs` | List analysis runs |
| GET | `/jobs` | List all jobs |

All responses follow: `{ success, data, error, timestamp }`

---

## Environment Variables

See `.env.example` for full reference.

Key variables:
```env
DATABASE_URL=postgresql://mining:mining@postgres:5432/mining
WORKER_URL=http://worker:8000
OPENAI_API_KEY=          # Optional: enables GPT-4 commentary
USE_MOCK_LLM=false       # Force mock even with API key
MAX_FILE_SIZE_MB=500
```

---

## Project Structure

```
mining/
├── apps/
│   ├── web/             # React + Vite + Tailwind frontend
│   └── api/             # NestJS REST API
├── services/
│   └── analysis-worker/ # Python FastAPI + DuckDB + Polars
├── packages/
│   └── shared/          # TypeScript type contracts
├── datasets/            # Demo CSV files + generator
├── infra/               # Docker Compose + DB init
├── docs/                # Architecture, phase docs
└── .github/workflows/   # CI/CD
```

---

## Roadmap

### Phase 2: Connector-Based Ingestion
- ServiceNow, Jira, Zendesk, Salesforce connectors
- Scheduled sync + incremental refresh
- Multi-source dataset merging

### Phase 3: Full Process Mining
- Event log construction from raw data
- Process discovery (DFG, Petri nets)
- Conformance checking against process models
- Bottleneck heatmaps

### Phase 4: Enterprise Intelligence Platform
- Multi-tenant architecture
- Role-based access control
- Custom insight rules engine
- Alert/notification system
- API for downstream systems

See [docs/phase1-mvp.md](docs/phase1-mvp.md) for Phase 1 scope details.
