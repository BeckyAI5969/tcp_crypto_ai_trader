#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="tcp_crypto_ai_trader"
APP_DIR="${APP_DIR:-$HOME/$APP_NAME}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
PYTHON_BIN="$VENV_DIR/bin/python"
PID_FILE="$APP_DIR/run/tcp_ai_trader.pid"
LOG_FILE="$APP_DIR/logs/application.log"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

fail() {
    printf '[ERROR] %s\n' "$1" >&2
    exit 1
}

if [[ ! -d "$APP_DIR" ]]; then
    fail "Project directory not found: $APP_DIR"
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    fail "Python virtual environment not found: $PYTHON_BIN"
fi

if [[ ! -f "$APP_DIR/start.py" ]]; then
    fail "start.py not found in $APP_DIR"
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
    fail ".env not found in $APP_DIR"
fi

mkdir -p "$APP_DIR/logs" "$APP_DIR/run"

if [[ -f "$PID_FILE" ]]; then
    EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null || true)"

    if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
        fail "Application is already running with PID $EXISTING_PID"
    fi

    rm -f "$PID_FILE"
fi

cd "$APP_DIR"

log "Running production readiness audit..."
"$PYTHON_BIN" -m src.production_readiness_audit

log "Starting TCP Crypto AI Trader..."
nohup "$PYTHON_BIN" start.py >> "$LOG_FILE" 2>&1 &
APP_PID=$!

echo "$APP_PID" > "$PID_FILE"

sleep 3

if kill -0 "$APP_PID" 2>/dev/null; then
    log "Application started successfully."
    log "PID: $APP_PID"
    log "Log: $LOG_FILE"
else
    rm -f "$PID_FILE"
    fail "Application failed to start. Check $LOG_FILE"
fi