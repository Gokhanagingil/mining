# Deploy Runbook

Operational guide for deploying, monitoring, and troubleshooting ProcessMiner.

---

## Table of Contents

1. [GitHub Secrets Setup](#1-github-secrets-setup)
2. [Automatic Deployment (Push to Main)](#2-automatic-deployment)
3. [Manual Deployment (Workflow Dispatch)](#3-manual-deployment)
4. [Post-Deploy Verification](#4-post-deploy-verification)
5. [Viewing Logs](#5-viewing-logs)
6. [Understanding Rollback](#6-understanding-rollback)
7. [Emergency Manual Recovery](#7-emergency-manual-recovery)
8. [Common Scenarios](#8-common-scenarios)

---

## 1. GitHub Secrets Setup

Navigate to your repository on GitHub:
**Settings** → **Secrets and variables** → **Actions**

### Required Secrets

| Secret | Example | Description |
|--------|---------|-------------|
| `DEPLOY_HOST` | `203.0.113.50` | Server IP address or hostname |
| `DEPLOY_PORT` | `22` | SSH port |
| `DEPLOY_USER` | `deploy` | SSH username |
| `DEPLOY_SSH_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` | Full private key content |
| `DEPLOY_PATH` | `/opt/mining` | Absolute path on the server |
| `APP_ENV_FILE` | *(see below)* | Full `.env` file content |

### Optional Secrets

| Secret | Example | Description |
|--------|---------|-------------|
| `DEPLOY_KNOWN_HOSTS` | `203.0.113.50 ssh-ed25519 AAAA...` | SSH host key verification |

### APP_ENV_FILE Content

This secret contains the full `.env` file. Example:

```env
DATABASE_URL=postgresql://mining:YOUR_SECURE_PASSWORD@postgres:5432/mining
STORAGE_PATH=/data/storage
PARQUET_PATH=/data/parquet
MAX_FILE_SIZE_MB=500
WORKER_URL=http://worker:8000
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
USE_MOCK_LLM=false
VITE_API_URL=http://YOUR_SERVER_IP:3001
CORS_ORIGIN=http://YOUR_SERVER_IP:5173
```

> **Important**: Replace `YOUR_SECURE_PASSWORD` with a strong password and `YOUR_SERVER_IP` with your actual server IP.

### Optional Variables

Navigate to **Settings** → **Secrets and variables** → **Actions** → **Variables** tab:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPOSE_PROJECT_NAME` | `mining` | Docker Compose project name |

### Setting Up the Production Environment

For approval gates and deployment protection:

1. Go to **Settings** → **Environments**
2. Click **New environment** → name it `production`
3. Optional: Add **Required reviewers** for manual approval before deploy
4. Optional: Add **Wait timer** for delayed deployments
5. Optional: Restrict to `main` branch under **Deployment branches**

---

## 2. Automatic Deployment

Every push to `main` (including merged PRs) triggers the deploy workflow automatically.

### Flow:

```
Push/Merge to main
  → Pre-deploy validation (compose config check, script validation)
  → SSH to server
  → Git pull latest code
  → Write .env file
  → docker compose build + up
  → Health checks (API, Worker, Web)
  → On failure: automatic rollback
```

### What triggers a deploy:

- Direct push to `main`
- PR merged into `main`
- GitHub web editor commits to `main`

### What does NOT trigger a deploy:

- Pushes to feature branches
- PR creation or updates
- Tag creation

---

## 3. Manual Deployment

### Via GitHub UI:

1. Go to **Actions** → **Deploy to Production**
2. Click **Run workflow**
3. Select branch: `main`
4. Optional: check "Skip health checks" for emergency deploys
5. Click **Run workflow**

### When to use manual deploy:

- Re-deploy the same version (e.g., after server restart)
- Deploy after updating `APP_ENV_FILE` secret
- Emergency re-deploy without code changes
- First-time deployment to a new server

---

## 4. Post-Deploy Verification

### Automatic (in workflow):

The workflow automatically runs health checks:

| Check | What it verifies |
|-------|-----------------|
| Container status | At least 3 containers running (api, worker, web) |
| API `/health` | Returns HTTP 200 with `{"status":"ok"}` |
| Worker `/health` | Returns HTTP 200 with `{"status":"ok"}` |
| Web `/` | Returns HTTP 200 |

Health checks retry up to 12 times with 5-second intervals (total ~60 seconds).

### Manual verification:

After deploy, you can verify manually:

```bash
# SSH to server
ssh deploy@YOUR_SERVER_IP

# Check container status
cd /opt/mining/infra
docker compose --env-file /opt/mining/.env ps

# Check health endpoints
curl http://localhost:3001/health
curl http://localhost:8000/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/

# Check logs
docker compose --env-file /opt/mining/.env logs --tail=50 api
docker compose --env-file /opt/mining/.env logs --tail=50 worker
docker compose --env-file /opt/mining/.env logs --tail=50 web
```

### From your browser:

- Web UI: `http://YOUR_SERVER_IP:5173`
- API Health: `http://YOUR_SERVER_IP:3001/health`
- API Docs (Swagger): `http://YOUR_SERVER_IP:3001/api`

---

## 5. Viewing Logs

### GitHub Actions logs:

1. Go to **Actions** tab in the repository
2. Click on the workflow run
3. Expand the **Deploy to Production Server** job
4. Each step shows its output

### Server-side logs:

```bash
# All services
cd /opt/mining/infra
docker compose --env-file /opt/mining/.env logs

# Specific service
docker compose --env-file /opt/mining/.env logs api
docker compose --env-file /opt/mining/.env logs worker
docker compose --env-file /opt/mining/.env logs web
docker compose --env-file /opt/mining/.env logs postgres

# Follow logs in real-time
docker compose --env-file /opt/mining/.env logs -f api

# Last N lines
docker compose --env-file /opt/mining/.env logs --tail=100 api
```

### Check which version is deployed:

```bash
cd /opt/mining
git log --oneline -1
cat .deploy-previous-sha
```

---

## 6. Understanding Rollback

### Automatic rollback:

If health checks fail after deploy, the workflow automatically:

1. Reads the previously saved commit SHA from `.deploy-previous-sha`
2. Checks out that commit
3. Rebuilds and restarts containers
4. Runs health checks on the rolled-back version
5. If rollback health check passes: workflow fails (but service is restored)
6. If rollback health check fails: workflow fails with CRITICAL error

### What rollback preserves:

- ✅ All database data (PostgreSQL volumes)
- ✅ All uploaded files (storage volumes)
- ✅ The `.env` file (not reverted)
- ✅ Docker volumes

### What rollback changes:

- ⚠️ Application code reverts to previous version
- ⚠️ Docker images are rebuilt from previous code

### When rollback does NOT help:

- Database migration issues (schema changes)
- Corrupted Docker volumes
- Infrastructure problems (disk full, network issues)

### Identifying a rollback in logs:

Look for these messages in the GitHub Actions output:

```
HEALTH CHECK FAILED — initiating rollback
[rollback] Starting rollback procedure
[rollback] Rolling back to commit: abc1234...
[rollback] Rollback complete.
```

---

## 7. Emergency Manual Recovery

If automated deployment and rollback both fail, connect to the server manually.

### Stop all services:

```bash
ssh deploy@YOUR_SERVER_IP
cd /opt/mining/infra
docker compose --env-file /opt/mining/.env down
```

### Check what went wrong:

```bash
# Check disk space
df -h

# Check Docker status
docker system df
docker ps -a

# Check logs for crash reasons
docker compose --env-file /opt/mining/.env logs --tail=100
```

### Manual rollback to a specific commit:

```bash
cd /opt/mining
git log --oneline -10  # Find a known good commit
git checkout <good-commit-sha>
cd infra
docker compose --env-file /opt/mining/.env up -d --build
```

### Restart without rebuilding:

```bash
cd /opt/mining/infra
docker compose --env-file /opt/mining/.env restart
```

### Full clean restart (keeps data):

```bash
cd /opt/mining/infra
docker compose --env-file /opt/mining/.env down
docker compose --env-file /opt/mining/.env up -d --build
```

### Nuclear option — full rebuild (keeps data volumes):

```bash
cd /opt/mining/infra
docker compose --env-file /opt/mining/.env down --rmi all
docker compose --env-file /opt/mining/.env up -d --build
```

> **Warning**: `--rmi all` removes all images. This forces a complete rebuild but does NOT delete data volumes.

### Return to main branch after manual recovery:

```bash
cd /opt/mining
git checkout main
git pull origin main
cd infra
docker compose --env-file /opt/mining/.env up -d --build
```

---

## 8. Common Scenarios

### Scenario: Update environment variables

1. Update the `APP_ENV_FILE` secret in GitHub
2. Trigger a manual deploy (Actions → Run workflow)
3. The new `.env` will be written to the server

### Scenario: Database needs manual migration

```bash
ssh deploy@YOUR_SERVER_IP
cd /opt/mining/infra

# Access PostgreSQL
docker compose --env-file /opt/mining/.env exec postgres psql -U mining -d mining

# Run your SQL commands
```

### Scenario: Server was restarted

Docker containers have `restart: unless-stopped`, so they should auto-restart. If not:

```bash
ssh deploy@YOUR_SERVER_IP
cd /opt/mining/infra
docker compose --env-file /opt/mining/.env up -d
```

### Scenario: Disk is filling up

```bash
# Check what's using space
docker system df -v

# Safe cleanup (removes only unused images, NOT volumes)
docker image prune -f

# Check application logs
du -sh /var/lib/docker/containers/*
```

### Scenario: Roll back to a specific version

```bash
ssh deploy@YOUR_SERVER_IP
cd /opt/mining

# List recent commits
git log --oneline -20

# Deploy a specific version
git checkout <commit-sha>
cd infra
docker compose --env-file /opt/mining/.env up -d --build
```

### Scenario: First deploy to a brand new server

1. Complete the [Server Setup Guide](./PRODUCTION_SERVER_SETUP.md)
2. Configure all [GitHub Secrets](#1-github-secrets-setup)
3. Go to Actions → Deploy to Production → Run workflow
4. The first deploy will clone the repository automatically
5. Verify with manual health checks
