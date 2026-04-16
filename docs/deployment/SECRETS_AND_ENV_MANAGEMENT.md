# Secrets & Environment Management

This document covers how secrets and environment variables are managed for ProcessMiner deployment.

---

## Current Approach (v1)

In the initial deployment setup, all environment configuration is managed through **GitHub Secrets**. The full `.env` file content is stored as a single secret (`APP_ENV_FILE`) and written to the server during each deployment.

### Why This Approach

- **Simple**: One secret contains all configuration
- **Centralized**: GitHub is the single source of truth
- **Auditable**: GitHub Secrets have audit logs
- **No additional tooling**: No Vault, no config management

### Limitations

- Editing a multi-line secret in GitHub UI is awkward
- No per-variable change tracking
- Entire `.env` is rewritten on every deploy
- Secret values are not validated before deploy
- Team members need repo admin access to manage secrets

---

## GitHub Secrets Reference

### Required Secrets

These must be set before the first deploy.

| Secret | Type | Example | Notes |
|--------|------|---------|-------|
| `DEPLOY_HOST` | string | `203.0.113.50` | Server IP or hostname |
| `DEPLOY_PORT` | string | `22` | SSH port number |
| `DEPLOY_USER` | string | `deploy` | SSH user (must have docker access) |
| `DEPLOY_SSH_KEY` | multiline | `-----BEGIN OPENSSH PRIVATE KEY-----`... | Full private key, including headers |
| `DEPLOY_PATH` | string | `/opt/mining` | Absolute path on server |
| `APP_ENV_FILE` | multiline | *(see below)* | Full .env file content |

### Optional Secrets

| Secret | Type | Example | Notes |
|--------|------|---------|-------|
| `DEPLOY_KNOWN_HOSTS` | string | `203.0.113.50 ssh-ed25519 AAAA...` | Prevents MITM attacks; auto-scanned if not set |

### GitHub Variables (non-sensitive)

Set under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPOSE_PROJECT_NAME` | `mining` | Docker Compose project name |

---

## APP_ENV_FILE Template

This is the full `.env` content to store in the `APP_ENV_FILE` secret:

```env
# ─── Database ───────────────────────────────
# This URL is for inter-container communication (docker network)
DATABASE_URL=postgresql://mining:CHANGE_THIS_PASSWORD@postgres:5432/mining

# ─── Storage ────────────────────────────────
STORAGE_PATH=/data/storage
PARQUET_PATH=/data/parquet
MAX_FILE_SIZE_MB=500

# ─── Worker ─────────────────────────────────
WORKER_URL=http://worker:8000

# ─── LLM ────────────────────────────────────
# Leave empty to use built-in mock commentary
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
USE_MOCK_LLM=false

# ─── Frontend ──────────────────────────────
# URL of the API as seen from the browser (use your server's IP or domain)
VITE_API_URL=http://YOUR_SERVER_IP:3001

# ─── CORS ───────────────────────────────────
# Set to your frontend URL for security
CORS_ORIGIN=http://YOUR_SERVER_IP:5173

# ─── Postgres Container ────────────────────
# These are used by the postgres service in docker-compose.yml
POSTGRES_DB=mining
POSTGRES_USER=mining
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD
```

### Important notes on APP_ENV_FILE:

1. **CHANGE_THIS_PASSWORD**: Replace with a strong, unique password. Use the same password in both `DATABASE_URL` and `POSTGRES_PASSWORD`.
2. **YOUR_SERVER_IP**: Replace with your actual server IP address.
3. **OPENAI_API_KEY**: Optional. Leave empty to use the built-in mock LLM.
4. **VITE_API_URL**: This is used at Docker build time for the frontend. It must be reachable from the user's browser.

---

## How Secrets Flow

```
GitHub Secret (APP_ENV_FILE)
    │
    ▼
GitHub Actions Runner (encrypted in memory)
    │
    ▼ base64 encoded, sent via SSH
    │
Remote Server
    │
    ▼ base64 decoded, written to file
    │
/opt/mining/.env (chmod 600, owned by deploy user)
    │
    ▼ read by docker compose
    │
Container environment variables
```

### Security properties:

- Secrets are encrypted at rest in GitHub
- Secrets are masked in workflow logs
- SSH transport is encrypted
- `.env` file has restricted permissions (600)
- `.env` is in `.gitignore` (never committed)

---

## Updating Secrets

### To update environment variables:

1. Go to **Settings → Secrets and variables → Actions**
2. Click on `APP_ENV_FILE`
3. Click **Update**
4. Paste the full updated `.env` content
5. Click **Update secret**
6. Trigger a new deploy (push to main or manual dispatch)

### To update SSH credentials:

1. Update `DEPLOY_SSH_KEY` with the new private key
2. Update `DEPLOY_KNOWN_HOSTS` if the server key changed
3. Ensure the new public key is in the server's `~/.ssh/authorized_keys`

---

## Environment Variable Reference

### Variables used by Docker Compose services:

| Variable | Used By | Description |
|----------|---------|-------------|
| `DATABASE_URL` | api | PostgreSQL connection string |
| `WORKER_URL` | api | Internal URL to analysis worker |
| `STORAGE_PATH` | api | File storage path (inside container) |
| `PARQUET_PATH` | api | Parquet storage path (inside container) |
| `PORT` | api | API listening port (default: 3001) |
| `NODE_ENV` | api | Node environment (production) |
| `CORS_ORIGIN` | api | Allowed CORS origin |
| `MAX_FILE_SIZE_MB` | api, worker | Maximum upload file size |
| `WORKER_STORAGE_PATH` | worker | Worker file storage path |
| `WORKER_PARQUET_PATH` | worker | Worker Parquet path |
| `WORKER_ARTIFACTS_PATH` | worker | Worker artifacts path |
| `WORKER_DATABASE_URL` | worker | Worker DB connection |
| `WORKER_OPENAI_API_KEY` | worker | OpenAI API key |
| `WORKER_OPENAI_MODEL` | worker | OpenAI model name |
| `WORKER_USE_MOCK_LLM` | worker | Force mock LLM |
| `OPENAI_API_KEY` | worker (via compose) | Mapped to WORKER_OPENAI_API_KEY |
| `OPENAI_MODEL` | worker (via compose) | Mapped to WORKER_OPENAI_MODEL |
| `USE_MOCK_LLM` | worker (via compose) | Mapped to WORKER_USE_MOCK_LLM |
| `VITE_API_URL` | web (build-time) | API URL for frontend |
| `POSTGRES_DB` | postgres | Database name |
| `POSTGRES_USER` | postgres | Database user |
| `POSTGRES_PASSWORD` | postgres | Database password |

### Variable precedence in Docker Compose:

1. Variables set directly in `docker-compose.yml` `environment:` block
2. Variables from `.env` file (via `${VAR:-default}` syntax)
3. Shell environment variables

---

## Future Evolution

### Phase 2: Server-Side Environment Management

As the deployment matures, consider migrating from GitHub Secrets to server-side configuration:

```
Current (v1):
  GitHub Secret → SSH → .env file → containers

Future (v2):
  Server-side config management → .env file → containers
  (e.g., HashiCorp Vault, AWS SSM, encrypted file on server)
```

Benefits of server-side management:
- Environment variables managed independently of deployments
- Per-variable change tracking
- Role-based access to secrets
- Secret rotation without triggering deploy
- Multiple environments from the same workflow

### Migration path:

1. Deploy workflow checks if `.env` exists on server
2. If it does AND `APP_ENV_FILE` is empty, use the existing server-side `.env`
3. If `APP_ENV_FILE` is provided, it always takes precedence (current behavior)
4. This allows gradual migration: stop setting `APP_ENV_FILE` once server-side management is in place

### Phase 3: Per-Service Environment Files

Instead of one `.env` file, each service gets its own:

```
/opt/mining/
├── .env                    # Shared variables
├── .env.api                # API-specific
├── .env.worker             # Worker-specific
└── .env.postgres           # Database-specific
```

This requires updating `docker-compose.yml` to use `env_file:` directives per service.

---

## Security Checklist

- [ ] Strong, unique PostgreSQL password (not the default "mining")
- [ ] `DEPLOY_SSH_KEY` is a dedicated key (not your personal SSH key)
- [ ] `DEPLOY_KNOWN_HOSTS` is set (prevents MITM)
- [ ] `.env` file permissions are 600 on the server
- [ ] `CORS_ORIGIN` is set to the specific frontend URL (not `*`)
- [ ] `OPENAI_API_KEY` has usage limits set in the OpenAI dashboard
- [ ] GitHub repository access is restricted to trusted team members
- [ ] `production` environment has required reviewers (optional but recommended)
