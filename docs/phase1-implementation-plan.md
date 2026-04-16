# Phase 1 Implementation Plan: AI Process Analyzer Foundation

## Overview

This document outlines the implementation plan for Phase 1 of the AI Process Analyzer platform.

## Architecture Decision: Evidence-First Pipeline

The core philosophy:
```
Upload → Profiling → Semantic Inference → Quality Gate → Deterministic Metrics → Evidence Pack → LLM Commentary
```

LLM **never** sees raw CSV. It only sees a structured evidence pack derived from deterministic analysis.

## Monorepo Structure

```
mining/
├── apps/
│   ├── web/                    # React + Vite + TypeScript + Tailwind + shadcn/ui
│   └── api/                    # NestJS + TypeScript
├── services/
│   └── analysis-worker/        # Python + FastAPI + DuckDB + Polars
├── packages/
│   └── shared/                 # Shared types/contracts between apps
├── infra/
│   ├── docker-compose.yml
│   └── init.sql
├── datasets/
│   ├── password-reset-spike.csv
│   └── customer-assignee-performance.csv
├── docs/
│   ├── architecture.md
│   ├── phase1-mvp.md
│   └── phase1-implementation-plan.md
└── .github/
    └── workflows/
        └── ci.yml
```

## Implementation Phases

### Phase 1a: Foundation (Monorepo + Shared Types + DB Schema)
- Package.json workspaces setup
- Shared TypeScript types for all data contracts
- PostgreSQL schema (all tables)
- Docker Compose with postgres, api, web, worker

### Phase 1b: Python Analysis Worker
- FastAPI service with proper job management
- DuckDB + Polars based CSV profiling engine
- Streaming/chunked approach for large files (up to 1M rows)
- Semantic column inference engine
- Deterministic metrics engine
- Insight candidate generator
- LLM evidence pack builder
- LLM commentary layer (with OpenAI adapter + mock fallback)

### Phase 1c: NestJS API
- Dataset upload with multipart handling
- Dataset state machine (uploaded → profiling → awaiting-mapping → analyzing → completed → failed)
- All CRUD endpoints
- Job orchestration (calling Python worker)
- Results storage and retrieval

### Phase 1d: React Frontend
- Upload page with progress
- Dataset list/detail pages
- Profiling/schema inference page
- Mapping review page
- Analysis results dashboard
- Insight detail drawers
- Jobs page

### Phase 1e: CI/CD + Documentation

## Key Technical Decisions

### Storage
- PostgreSQL for all metadata and structured results
- Local filesystem (with storage adapter abstraction) for files/artifacts
- Parquet as intermediate format after CSV upload
- MinIO-compatible abstraction ready for later S3 migration

### Analysis Stack
- DuckDB: SQL-based aggregations over Parquet (fast, memory-efficient)
- Polars: DataFrame operations for profiling (lazy evaluation)
- PyArrow: Parquet read/write

### Scale Target
- 1,000,000 rows × 100 columns
- Chunked CSV parsing (never load full file into RAM)
- Approximate distinct counts for high-cardinality columns
- Async job execution

### Semantic Inference Strategy
Column name patterns + data type + value distribution → semantic role
Confidence scoring based on:
1. Name pattern match strength
2. Data type compatibility
3. Value distribution fit
4. Format pattern recognition

### Insight Ranking
Insights ranked by: support_count × effect_size × actionability_score
Top 10 surfaced to LLM for commentary

## Demo Datasets
1. `password-reset-spike.csv`: IT helpdesk tickets with Monday morning password reset spikes
2. `customer-assignee-performance.csv`: Support tickets showing assignee performance gaps and customer-specific patterns

## Risk Register
| Risk | Decision |
|------|----------|
| LLM hallucination | Evidence pack forces grounding; mock fallback ensures deterministic output |
| Large file OOM | Polars lazy + DuckDB COPY; never full pandas read |
| Semantic inference ambiguity | Low confidence shown in UI; user confirmation flow |
| OpenAI latency | Async jobs; non-blocking UI |
| Phase 2 schema evolution | Tables designed with extensibility columns (metadata JSONB) |
