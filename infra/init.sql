-- Mining Platform - PostgreSQL Init Script
-- Tables are auto-created by TypeORM synchronize in Phase 1.
-- This script sets up extensions and initial config.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Performance indexes (created alongside TypeORM sync)
-- Additional manual indexes can be added here post-schema-creation.
