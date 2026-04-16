# Deployment Implementation Plan

## Objective

Set up a production-ready, single-server deployment workflow for the ProcessMiner monorepo using GitHub Actions and Docker Compose over SSH.

## Current State

- Monorepo: `apps/web`, `apps/api`, `services/analysis-worker`, `packages/shared`
- Docker Compose at `infra/docker-compose.yml` orchestrates 4 services (postgres, api, web, worker)
- CI pipeline exists at `.github/workflows/ci.yml` (lint, test, docker smoke check)
- No automated deployment exists
- Health endpoints: API (`/health`), Worker (`/health`), Web (HTTP 200 on `/`)

## Target State

GitHub Actions workflow that deploys to a single Ubuntu/Debian server on `main` branch push or manual dispatch, with health verification and automatic rollback on failure.

## Implementation Components

### A. GitHub Actions Workflow (`.github/workflows/deploy.yml`)

- Triggers: `push` on `main`, `workflow_dispatch`
- Concurrency: `production-deploy` (cancel-in-progress: false, queue deployments)
- Environment: `production` (GitHub Environment for approval gates)
- Steps: SSH into server → pull latest code → write .env → docker compose up → health check → rollback on failure

### B. Deploy Scripts

| Script | Purpose |
|--------|---------|
| `scripts/deploy-remote.sh` | Main deploy logic: git pull, write env, compose up, cleanup |
| `scripts/health-check.sh` | Post-deploy health verification with retry logic |
| `scripts/rollback-remote.sh` | Rollback to previous commit SHA on health check failure |

### C. Documentation

| Document | Path |
|----------|------|
| Server Setup Guide | `docs/deployment/PRODUCTION_SERVER_SETUP.md` |
| Deploy Runbook | `docs/deployment/DEPLOY_RUNBOOK.md` |
| Secrets & Env Guide | `docs/deployment/SECRETS_AND_ENV_MANAGEMENT.md` |

### D. README Update

Add "Deployment" section to root `README.md` with links to deployment docs.

## Secret/Variable Design

### GitHub Secrets (sensitive)

| Secret | Description |
|--------|-------------|
| `DEPLOY_HOST` | Server IP or hostname |
| `DEPLOY_PORT` | SSH port (default 22) |
| `DEPLOY_USER` | SSH user on server |
| `DEPLOY_SSH_KEY` | Private SSH key for authentication |
| `DEPLOY_PATH` | Absolute path on server (e.g., `/opt/mining`) |
| `APP_ENV_FILE` | Full `.env` file contents |
| `DEPLOY_KNOWN_HOSTS` | SSH known_hosts entry (optional) |

### GitHub Variables or workflow env (non-sensitive)

| Variable | Description |
|----------|-------------|
| `COMPOSE_PROJECT_NAME` | Docker Compose project name (default: `mining`) |

## Deploy Flow

```
1. Workflow triggered (push to main or manual dispatch)
2. SSH connection established
3. Save current commit SHA for rollback
4. Git fetch + checkout main + pull
5. Write .env from secret
6. cd infra && docker compose up -d --build
7. Lightweight cleanup (dangling images only, no volume prune)
8. Health checks with retry (API /health, Worker /health, Web HTTP 200)
9. If health fails → rollback to saved SHA → compose up again → fail workflow
10. Success → log deploy summary
```

## Rollback Strategy

- Pre-deploy: record current HEAD SHA
- On health check failure: `git checkout <saved-sha>`, rebuild containers
- Rollback health check: if rollback also fails, workflow fails with clear error
- Data volumes are NEVER deleted during deploy or rollback

## Risks & Future Work

| Item | Status |
|------|--------|
| Reverse proxy (Nginx/Caddy) | Documented as future work |
| HTTPS/TLS | Documented as future work |
| Server-side env management (Vault, etc.) | Documented as future migration path |
| Multi-server deployment | Out of scope |
| Blue-green deployment | Out of scope for v1 |
| Monitoring stack | Out of scope for v1 |

## Acceptance Criteria

1. Deploy workflow file exists and is syntactically valid
2. Scripts are executable and use `set -euo pipefail`
3. Server setup guide covers all prerequisites
4. Runbook covers manual and automatic deploy flows
5. Secrets documentation is complete
6. Health check covers all three services
7. Rollback mechanism tested in workflow logic
8. README updated with deployment section
