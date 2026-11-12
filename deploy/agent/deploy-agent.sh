#!/usr/bin/env bash
# deploy-agent.sh - pull-based, digest-pinned deployer for TrueNAS (25.10+) Custom Apps.
# Usage: deploy-agent.sh [--dry-run] [--force] <agent.conf> [<agent.conf> ...]
# Run as root (cron task) on the NAS. See README.md and Documentation/ci-cd-pipeline-playbook.md.
set -uo pipefail

DRY_RUN=0; FORCE=0; CONFS=()
for a in "$@"; do
  case "$a" in
    --dry-run) DRY_RUN=1 ;;
    --force)   FORCE=1 ;;
    -h|--help) sed -n '2,4p' "$0"; exit 0 ;;
    *) CONFS+=("$a") ;;
  esac
done
[ "${#CONFS[@]}" -gt 0 ] || { echo "usage: $0 [--dry-run] [--force] <agent.conf>..." >&2; exit 2; }

log() { printf '%s [%s] %s\n' "$(date -u +%FT%TZ)" "${APP_NAME:-agent}" "$*"; }

# Extract services.<svc>.image from `midclt call app.config` JSON on stdin.
cfg_image() { python3 -c 'import json,sys; print(json.load(sys.stdin)["services"][sys.argv[1]]["image"])' "$1"; }

# Build the app.update payload: same config, only services.<svc>.image changed.
build_payload() {
  python3 -c '
import json,sys
svc,ref=sys.argv[1],sys.argv[2]
cfg=json.load(sys.stdin)
cfg["services"][svc]["image"]=ref
print(json.dumps({"custom_compose_config":cfg}))' "$1" "$2"
}

dcli() { DOCKER_CONFIG="${DOCKER_CONFIG_DIR}" docker "$@"; }

# Pull the watched pointer tag and print its manifest digest (sha256:...).
resolve_digest() {
  dcli pull -q "${IMAGE}:${WATCH_TAG}" >/dev/null || return 1
  dcli image inspect "${IMAGE}:${WATCH_TAG}" --format '{{range .RepoDigests}}{{println .}}{{end}}' \
    | grep -F "${IMAGE}@" | head -n1 | cut -d@ -f2
}

# Pull a specific digest so TrueNAS never has to fetch it during update.
pull_digest() { dcli pull -q "${IMAGE}@$1" >/dev/null; }

image_revision() { dcli image inspect "${IMAGE}@$1" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' 2>/dev/null || true; }

# Local image ID (sha256:...) for any image reference.
image_id() { dcli image inspect "$1" --format '{{.Id}}' 2>/dev/null || true; }

# The running container of this app's compose service (TrueNAS names the project ix-<app>).
service_container() {
  dcli ps -q --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" \
    --filter "label=com.docker.compose.service=${SERVICE}" | head -n1
}

# "<image-id> <health>" of the running service container; health is healthy|starting|unhealthy|none.
container_state() {
  local cid; cid="$(service_container)"; [ -n "$cid" ] || return 1
  dcli inspect "$cid" --format '{{.Image}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
}

# Digest reference for the image the service container runs now, so rollback never relies on a
# mutable tag (which the agent's own pull may already have moved). Falls back to the config ref.
running_ref() {
  local st id d; st="$(container_state)" || { printf '%s' "$1"; return; }
  id="${st%% *}"
  d="$(dcli image inspect "$id" --format '{{range .RepoDigests}}{{println .}}{{end}}' 2>/dev/null \
       | grep -F "${IMAGE}@" | head -n1)"
  printf '%s' "${d:-$1}"
}

# Healthy = the service container runs the expected image ID (if given), its Docker healthcheck
# (if defined) reports healthy, HEALTH_URL answers 2xx, and - only when HEALTH_SHA_FIELD is set and
# the image has a revision label - the health JSON reports that revision.
wait_healthy() {
  local expected_id="$1" expected_rev="${2:-}" deadline=$(( $(date +%s) + HEALTH_TIMEOUT )) body st
  while [ "$(date +%s)" -lt "$deadline" ]; do
    st="$(container_state)" || st=""
    if [ -n "$st" ] && { [ -z "$expected_id" ] || [ "${st%% *}" = "$expected_id" ]; } \
       && case "${st#* }" in healthy|none) true ;; *) false ;; esac \
       && body="$(curl -fsS --max-time 5 "$HEALTH_URL" 2>/dev/null)"; then
      if [ -z "$HEALTH_SHA_FIELD" ] || [ -z "$expected_rev" ]; then return 0; fi
      if printf '%s' "$body" | python3 -c '
import json,sys
field,exp=sys.argv[1],sys.argv[2]
def find(o):
    if isinstance(o,dict):
        if field in o: return o[field]
        for v in o.values():
            r=find(v)
            if r is not None: return r
    return None
got=str(find(json.load(sys.stdin)) or "")
sys.exit(0 if got and (exp.startswith(got) or got.startswith(exp)) else 1)' "$HEALTH_SHA_FIELD" "$expected_rev"; then
        return 0
      fi
    fi
    sleep 5
  done
  log "health wait timed out; last container state: ${st:-<no container for project ${COMPOSE_PROJECT}, service ${SERVICE}>}"
  return 1
}

state_get() { [ -f "$STATE_FILE" ] && sed -n "s/^$1=//p" "$STATE_FILE" | tail -n1 || true; }
state_set() { # key value
  touch "$STATE_FILE"
  grep -v "^$1=" "$STATE_FILE" > "$STATE_FILE.tmp" || true
  printf '%s=%s\n' "$1" "$2" >> "$STATE_FILE.tmp"; mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# TrueNAS app state: RUNNING | DEPLOYING | STOPPED | CRASHED | ...
app_state() {
  midclt call app.query "[[\"name\", \"=\", \"${APP_NAME}\"]]" \
    | python3 -c 'import json, sys; r = json.load(sys.stdin); print(r[0].get("state", "") if r else "")'
}

apply_ref() { # ref -> app.update (+ app.start if the app is stopped)
  local payload st out
  payload="$(midclt call app.config "$APP_NAME" | build_payload "$SERVICE" "$1")" || return 1
  if [ "$DRY_RUN" = 1 ]; then log "DRY-RUN payload: $payload"; return 0; fi
  # app.update is a middleware job: -j waits for it and exits non-zero if the job fails.
  # Its progress output is kept quiet; the last lines are logged if it fails.
  out="$(midclt call -j app.update "$APP_NAME" "$payload" 2>&1)" \
    || { log "ERROR: app.update failed: $(printf '%s' "$out" | tail -n 3)"; return 1; }
  # Updating a stopped app only changes its config; start it so the new image actually runs.
  st="$(app_state)" || st=""
  case "$st" in
    STOPPED|CRASHED)
      log "app is ${st}; starting it"
      out="$(midclt call -j app.start "$APP_NAME" 2>&1)" \
        || { log "ERROR: app.start failed: $(printf '%s' "$out" | tail -n 3)"; return 1; } ;;
  esac
}

process() {
  # shellcheck disable=SC1090
  . "$1"
  : "${APP_NAME:?}" "${IMAGE:?}" "${WATCH_TAG:?}" "${HEALTH_URL:?}" "${STATE_DIR:?}"
  SERVICE="${SERVICE:-web}"; HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-180}"; AUTO_APPLY="${AUTO_APPLY:-1}"
  HEALTH_SHA_FIELD="${HEALTH_SHA_FIELD:-}"; DOCKER_CONFIG_DIR="${DOCKER_CONFIG_DIR:-$STATE_DIR/docker}"
  COMPOSE_PROJECT="${COMPOSE_PROJECT:-ix-$APP_NAME}"; BACKUP_CMD="${BACKUP_CMD:-}"
  mkdir -p "$STATE_DIR"; STATE_FILE="$STATE_DIR/$APP_NAME.state"

  exec 9>"$STATE_DIR/$APP_NAME.lock"
  flock -n 9 || { log "another run in progress; skipping"; return 0; }

  local new cur_ref cur_digest failed rev
  new="$(resolve_digest)" || { log "ERROR: cannot resolve ${IMAGE}:${WATCH_TAG} (registry login/network?)"; return 1; }
  [ -n "$new" ] || { log "ERROR: no digest found for ${IMAGE}:${WATCH_TAG}"; return 1; }

  cur_ref="$(midclt call app.config "$APP_NAME" | cfg_image "$SERVICE")" \
    || { log "ERROR: cannot read app config"; return 1; }
  cur_digest=""; case "$cur_ref" in *@sha256:*) cur_digest="${cur_ref#*@}" ;; esac

  if [ "$new" = "$cur_digest" ] && [ "$FORCE" = 0 ]; then log "up to date ($new)"; return 0; fi
  failed="$(state_get FAILED)"
  if [ "$new" = "$failed" ] && [ "$FORCE" = 0 ]; then log "skipping $new: previously failed (use --force to retry)"; return 0; fi
  if [ "$AUTO_APPLY" != 1 ] && [ "$FORCE" = 0 ]; then log "update available $new (AUTO_APPLY=0, not applying)"; return 0; fi

  local rollback_ref run_state new_id
  rollback_ref="$(running_ref "$cur_ref")"
  run_state="$(container_state)" || run_state="<none found>"
  log "deploying ${IMAGE}@${new} (was: ${cur_ref})"
  log "running container (project ${COMPOSE_PROJECT}, service ${SERVICE}): ${run_state}; rollback target: ${rollback_ref}"
  if [ "$DRY_RUN" = 1 ]; then apply_ref "${IMAGE}@${new}"; return 0; fi

  pull_digest "$new" || { log "ERROR: pull of digest failed"; return 1; }
  new_id="$(image_id "${IMAGE}@${new}")"
  [ -n "$new_id" ] || { log "ERROR: cannot read image ID of ${IMAGE}@${new}"; return 1; }

  if [ -n "$BACKUP_CMD" ]; then
    log "running pre-deploy backup"
    if ! bash -c "$BACKUP_CMD"; then log "ERROR: backup failed; aborting deploy"; return 1; fi
  fi

  rev="$(image_revision "$new")"
  if apply_ref "${IMAGE}@${new}" && wait_healthy "$new_id" "$rev"; then
    state_set PREVIOUS "$rollback_ref"; state_set DEPLOYED "$new"; state_set FAILED ""
    log "SUCCESS: $new healthy (revision ${rev:-unknown})"; return 0
  fi

  log "ERROR: $new did not become healthy; rolling back to $rollback_ref"
  state_set FAILED "$new"
  if apply_ref "$rollback_ref" && wait_healthy "$(image_id "$rollback_ref")"; then log "rollback OK"; else log "CRITICAL: rollback did not return healthy; manual action needed"; fi
  return 1
}

rc=0
for c in "${CONFS[@]}"; do ( process "$c" ) || rc=1; done
exit $rc
