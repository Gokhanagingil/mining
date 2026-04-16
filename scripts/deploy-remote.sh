#!/usr/bin/env bash
set -euo pipefail

# ─── Deploy Remote Script ────────────────────────────────────────────────────
# Runs ON the remote server via SSH.
# Pulls latest code, writes .env, rebuilds containers, runs cleanup.
#
# Required environment variables:
#   DEPLOY_PATH       - Absolute path to the project on the server
#   REPO_URL          - Git clone URL (HTTPS)
#   APP_ENV_CONTENT   - Full .env file contents (base64 encoded)
#   GIT_REF           - Git ref to deploy (default: main)
#
# Optional:
#   COMPOSE_PROJECT_NAME - Docker Compose project name (default: mining)
# ─────────────────────────────────────────────────────────────────────────────

DEPLOY_PATH="${DEPLOY_PATH:?DEPLOY_PATH is required}"
REPO_URL="${REPO_URL:?REPO_URL is required}"
APP_ENV_CONTENT="${APP_ENV_CONTENT:-}"
GIT_REF="${GIT_REF:-main}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-mining}"

INFRA_DIR="${DEPLOY_PATH}/infra"
ENV_FILE="${DEPLOY_PATH}/.env"
PREVIOUS_SHA_FILE="${DEPLOY_PATH}/.deploy-previous-sha"

log() {
  echo "[deploy] $(date '+%Y-%m-%d %H:%M:%S') $*"
}

error() {
  echo "[deploy] ERROR: $*" >&2
}

# ─── Step 1: Ensure deploy directory and repo exist ──────────────────────────

log "═══════════════════════════════════════════════════════════"
log "Starting deployment to ${DEPLOY_PATH}"
log "Git ref: ${GIT_REF}"
log "═══════════════════════════════════════════════════════════"

if [ ! -d "${DEPLOY_PATH}/.git" ]; then
  log "Repository not found at ${DEPLOY_PATH}, cloning..."
  mkdir -p "$(dirname "${DEPLOY_PATH}")"
  git clone "${REPO_URL}" "${DEPLOY_PATH}"
  cd "${DEPLOY_PATH}"
  log "Clone complete."
else
  cd "${DEPLOY_PATH}"
  log "Repository exists, fetching latest..."
fi

# ─── Step 2: Save current SHA for rollback ───────────────────────────────────

CURRENT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "none")
log "Current commit SHA: ${CURRENT_SHA}"
echo "${CURRENT_SHA}" > "${PREVIOUS_SHA_FILE}"

# ─── Step 3: Pull latest code ───────────────────────────────────────────────

log "Fetching and checking out ${GIT_REF}..."
git fetch origin "${GIT_REF}"
git checkout "${GIT_REF}" 2>/dev/null || git checkout -b "${GIT_REF}" "origin/${GIT_REF}"
git reset --hard "origin/${GIT_REF}"

NEW_SHA=$(git rev-parse HEAD)
log "Deployed commit SHA: ${NEW_SHA}"

if [ "${CURRENT_SHA}" = "${NEW_SHA}" ]; then
  log "Same commit as currently deployed. Continuing anyway (may be re-deploy)."
fi

# ─── Step 4: Write .env file ────────────────────────────────────────────────

if [ -n "${APP_ENV_CONTENT}" ]; then
  log "Writing .env file..."
  echo "${APP_ENV_CONTENT}" | base64 -d > "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  log ".env file written ($(wc -l < "${ENV_FILE}") lines)."
else
  if [ -f "${ENV_FILE}" ]; then
    log "No APP_ENV_CONTENT provided. Using existing .env file."
  else
    log "WARNING: No .env file exists and no APP_ENV_CONTENT provided."
    log "Copying .env.example as fallback..."
    if [ -f "${DEPLOY_PATH}/.env.example" ]; then
      cp "${DEPLOY_PATH}/.env.example" "${ENV_FILE}"
      chmod 600 "${ENV_FILE}"
    else
      error "No .env.example found either. Services may fail to start."
    fi
  fi
fi

# ─── Step 5: Build and start services ───────────────────────────────────────

log "Building and starting services..."
cd "${INFRA_DIR}"

export COMPOSE_PROJECT_NAME

docker compose --env-file "${ENV_FILE}" build --parallel 2>&1 | tail -20
log "Build complete."

docker compose --env-file "${ENV_FILE}" up -d 2>&1
log "Services started."

# ─── Step 6: Lightweight cleanup ────────────────────────────────────────────

log "Running lightweight cleanup (dangling images only)..."
docker image prune -f --filter "until=24h" 2>/dev/null || true
log "Cleanup complete."

# ─── Step 7: Show running containers ────────────────────────────────────────

log "Current container status:"
docker compose --env-file "${ENV_FILE}" ps

log "═══════════════════════════════════════════════════════════"
log "Deploy script complete. SHA: ${NEW_SHA}"
log "═══════════════════════════════════════════════════════════"
