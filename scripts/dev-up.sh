#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_DB="${REDIS_DB:-0}"
export GESHI_UPLOAD_DIR="${GESHI_UPLOAD_DIR:-$ROOT_DIR/tmp/uploads}"
export SCRIBE_HOST="${SCRIBE_HOST:-0.0.0.0}"
export SCRIBE_PORT="${SCRIBE_PORT:-58000}"

mkdir -p "$GESHI_UPLOAD_DIR"

pids=()

cleanup() {
  local exit_code="${1:-0}"
  trap - EXIT INT TERM

  if [ "${#pids[@]}" -gt 0 ]; then
    kill "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi

  exit "$exit_code"
}

trap 'cleanup $?' EXIT
trap 'cleanup 130' INT TERM

echo "Starting scribe api on ${SCRIBE_HOST}:${SCRIBE_PORT}"
uv run uvicorn src.main:app --host "$SCRIBE_HOST" --port "$SCRIBE_PORT" &
pids+=("$!")

echo "Starting scribe worker"
uv run python -m src.worker &
pids+=("$!")

echo "Starting scribe scheduler"
uv run python -m src.scheduler &
pids+=("$!")

wait -n "${pids[@]}"
cleanup $?
