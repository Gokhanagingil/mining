#!/usr/bin/env bash
set -euo pipefail

# ─── Health Check Script ─────────────────────────────────────────────────────
# Runs ON the remote server via SSH.
# Verifies all services are healthy after deployment.
#
# Required environment variables:
#   DEPLOY_PATH - Absolute path to the project on the server
#
# Optional:
#   HEALTH_CHECK_RETRIES  - Number of retry attempts (default: 12)
#   HEALTH_CHECK_INTERVAL - Seconds between retries (default: 5)
#   API_PORT              - API port (default: 3001)
#   WORKER_PORT           - Worker port (default: 8000)
#   WEB_PORT              - Web port (default: 5173)
# ─────────────────────────────────────────────────────────────────────────────

DEPLOY_PATH="${DEPLOY_PATH:?DEPLOY_PATH is required}"
HEALTH_CHECK_RETRIES="${HEALTH_CHECK_RETRIES:-12}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-5}"
API_PORT="${API_PORT:-3001}"
WORKER_PORT="${WORKER_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

INFRA_DIR="${DEPLOY_PATH}/infra"
ENV_FILE="${DEPLOY_PATH}/.env"
FAILED=0

log() {
  echo "[health] $(date '+%Y-%m-%d %H:%M:%S') $*"
}

error() {
  echo "[health] ERROR: $*" >&2
}

check_endpoint() {
  local name="$1"
  local url="$2"
  local expect_json="${3:-false}"

  log "Checking ${name} at ${url}..."

  for i in $(seq 1 "${HEALTH_CHECK_RETRIES}"); do
    HTTP_CODE=$(curl -s -o /tmp/health_response -w "%{http_code}" --max-time 10 "${url}" 2>/dev/null || echo "000")

    if [ "${HTTP_CODE}" = "200" ]; then
      if [ "${expect_json}" = "true" ]; then
        BODY=$(cat /tmp/health_response 2>/dev/null || echo "")
        STATUS=$(echo "${BODY}" | grep -o '"status":"ok"' 2>/dev/null || echo "")
        if [ -n "${STATUS}" ]; then
          log "✓ ${name}: healthy (HTTP ${HTTP_CODE}, status: ok)"
          return 0
        else
          log "  ${name}: HTTP 200 but status not 'ok' (attempt ${i}/${HEALTH_CHECK_RETRIES})"
        fi
      else
        log "✓ ${name}: healthy (HTTP ${HTTP_CODE})"
        return 0
      fi
    else
      log "  ${name}: HTTP ${HTTP_CODE} (attempt ${i}/${HEALTH_CHECK_RETRIES})"
    fi

    if [ "${i}" -lt "${HEALTH_CHECK_RETRIES}" ]; then
      sleep "${HEALTH_CHECK_INTERVAL}"
    fi
  done

  error "✗ ${name}: health check failed after ${HEALTH_CHECK_RETRIES} attempts"
  return 1
}

# ─── Pre-flight: Check Docker Compose status ────────────────────────────────

log "═══════════════════════════════════════════════════════════"
log "Starting health verification"
log "═══════════════════════════════════════════════════════════"

cd "${INFRA_DIR}"

log "Docker Compose service status:"
docker compose --env-file "${ENV_FILE}" ps
echo ""

RUNNING_COUNT=$(docker compose --env-file "${ENV_FILE}" ps --status running -q 2>/dev/null | wc -l || echo "0")
log "Running containers: ${RUNNING_COUNT}"

if [ "${RUNNING_COUNT}" -lt 3 ]; then
  error "Expected at least 3 running containers (api, worker, web), found ${RUNNING_COUNT}"
  log "Container logs (last 30 lines each):"
  for svc in api worker web postgres; do
    log "--- ${svc} ---"
    docker compose --env-file "${ENV_FILE}" logs --tail=30 "${svc}" 2>/dev/null || true
    echo ""
  done
  FAILED=1
fi

# ─── Health endpoint checks ─────────────────────────────────────────────────

if [ "${FAILED}" -eq 0 ]; then
  log "Waiting ${HEALTH_CHECK_INTERVAL}s before first health check..."
  sleep "${HEALTH_CHECK_INTERVAL}"
fi

log "Checking API health endpoint..."
if ! check_endpoint "API" "http://localhost:${API_PORT}/health" "true"; then
  FAILED=1
fi

log "Checking Worker health endpoint..."
if ! check_endpoint "Worker" "http://localhost:${WORKER_PORT}/health" "true"; then
  FAILED=1
fi

log "Checking Web endpoint..."
if ! check_endpoint "Web" "http://localhost:${WEB_PORT}/" "false"; then
  FAILED=1
fi

# ─── Result ──────────────────────────────────────────────────────────────────

echo ""
log "═══════════════════════════════════════════════════════════"

if [ "${FAILED}" -ne 0 ]; then
  error "HEALTH CHECK FAILED — one or more services are unhealthy"
  log "═══════════════════════════════════════════════════════════"
  exit 1
fi

log "ALL HEALTH CHECKS PASSED"
log "═══════════════════════════════════════════════════════════"
exit 0
