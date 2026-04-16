#!/usr/bin/env bash
set -euo pipefail

# ─── Rollback Remote Script ──────────────────────────────────────────────────
# Runs ON the remote server via SSH.
# Rolls back to the previous commit SHA and rebuilds containers.
#
# Required environment variables:
#   DEPLOY_PATH - Absolute path to the project on the server
#
# Optional:
#   ROLLBACK_SHA         - Specific SHA to roll back to (reads from .deploy-previous-sha if not set)
#   COMPOSE_PROJECT_NAME - Docker Compose project name (default: mining)
# ─────────────────────────────────────────────────────────────────────────────

DEPLOY_PATH="${DEPLOY_PATH:?DEPLOY_PATH is required}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-mining}"

INFRA_DIR="${DEPLOY_PATH}/infra"
ENV_FILE="${DEPLOY_PATH}/.env"
PREVIOUS_SHA_FILE="${DEPLOY_PATH}/.deploy-previous-sha"

log() {
  echo "[rollback] $(date '+%Y-%m-%d %H:%M:%S') $*"
}

error() {
  echo "[rollback] ERROR: $*" >&2
}

# ─── Determine rollback target ──────────────────────────────────────────────

log "═══════════════════════════════════════════════════════════"
log "Starting rollback procedure"
log "═══════════════════════════════════════════════════════════"

cd "${DEPLOY_PATH}"

CURRENT_SHA=$(git rev-parse HEAD)
log "Current (failed) SHA: ${CURRENT_SHA}"

if [ -n "${ROLLBACK_SHA:-}" ]; then
  TARGET_SHA="${ROLLBACK_SHA}"
  log "Using provided ROLLBACK_SHA: ${TARGET_SHA}"
elif [ -f "${PREVIOUS_SHA_FILE}" ]; then
  TARGET_SHA=$(cat "${PREVIOUS_SHA_FILE}")
  log "Using saved previous SHA: ${TARGET_SHA}"
else
  error "No ROLLBACK_SHA provided and no .deploy-previous-sha file found."
  error "Cannot determine rollback target."
  exit 1
fi

if [ "${TARGET_SHA}" = "none" ]; then
  error "Previous SHA is 'none' (first deploy). Cannot roll back."
  error "Manual intervention required."
  exit 1
fi

if [ "${TARGET_SHA}" = "${CURRENT_SHA}" ]; then
  error "Rollback SHA is the same as current SHA. Nothing to roll back to."
  exit 1
fi

# ─── Rollback git ───────────────────────────────────────────────────────────

log "Rolling back to commit: ${TARGET_SHA}"
git checkout "${TARGET_SHA}"

ACTUAL_SHA=$(git rev-parse HEAD)
log "HEAD is now at: ${ACTUAL_SHA}"

# ─── Rebuild containers ────────────────────────────────────────────────────

log "Rebuilding containers from rolled-back code..."
cd "${INFRA_DIR}"

export COMPOSE_PROJECT_NAME

docker compose --env-file "${ENV_FILE}" build --parallel 2>&1 | tail -20
log "Build complete."

docker compose --env-file "${ENV_FILE}" up -d 2>&1
log "Services restarted."

# ─── Show status ────────────────────────────────────────────────────────────

log "Container status after rollback:"
docker compose --env-file "${ENV_FILE}" ps

log "═══════════════════════════════════════════════════════════"
log "Rollback complete. Reverted from ${CURRENT_SHA} to ${TARGET_SHA}"
log "═══════════════════════════════════════════════════════════"
