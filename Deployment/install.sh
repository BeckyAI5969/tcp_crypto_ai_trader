#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="tcp_crypto_ai_trader"
APP_USER="${APP_USER:-$USER}"
APP_DIR="${APP_DIR:-$HOME/$APP_NAME}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

fail() {
    printf '[ERROR] %s\n' "$1" >&2
    exit 1
}

if [[ "${EUID}" -eq 0 ]]; then
    fail "Do not run this script as root. Run it as the deployment user."
fi

if ! command -v sudo >/dev/null 2>&1; then
    fail "sudo is required."
fi

if [[ ! -d "$APP_DIR" ]]; then
    fail "Project directory not found: $APP_DIR"
fi

if [[ ! -f "$APP_DIR/requirements.txt" ]]; then
    fail "requirements.txt not found in $APP_DIR"
fi

if [[ ! -f "$APP_DIR/start.py" ]]; then
    fail "start.py not found in $APP_DIR"
fi

log "Updating Ubuntu packages..."
sudo apt-get update

log "Installing system dependencies..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    curl \
    ca-certificates \
    tzdata

log "Setting server timezone to Asia/Bangkok..."
sudo timedatectl set-timezone Asia/Bangkok

log "Creating Python virtual environment..."
"$PYTHON_BIN" -m venv "$VENV_DIR"

log "Upgrading pip tooling..."
"$VENV_DIR/bin/python" -m pip install --upgrade \
    pip \
    setuptools \
    wheel

log "Installing Python dependencies..."
"$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

log "Creating runtime directories..."
mkdir -p \
    "$APP_DIR/logs" \
    "$APP_DIR/run"

log "Checking environment configuration..."
if [[ ! -f "$APP_DIR/.env" ]]; then
    if [[ -f "$APP_DIR/.env.example" ]]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        chmod 600 "$APP_DIR/.env"
        log "Created .env from .env.example"
        log "IMPORTANT: Fill in Binance Testnet and LINE credentials before starting."
    else
        fail ".env and .env.example are both missing."
    fi
else
    chmod 600 "$APP_DIR/.env"
    log ".env already exists."
fi

log "Running production readiness audit..."
cd "$APP_DIR"
set +e
"$VENV_DIR/bin/python" -m src.production_readiness_audit
AUDIT_STATUS=$?
set -e

if [[ "$AUDIT_STATUS" -ne 0 ]]; then
    fail "Production Readiness Audit failed. Fix all FAIL items before deployment."
fi

log "Installation completed successfully."
log "Project directory: $APP_DIR"
log "Virtual environment: $VENV_DIR"
log "Next step: configure $APP_DIR/.env"