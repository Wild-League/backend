#!/usr/bin/env bash
# vm-setup.sh — Run this ONCE on a fresh VM to prepare it for deployments.
#
# Usage:
#   1. SSH into your VM
#   2. curl -fsSL https://<your-repo>/raw/main/scripts/vm-setup.sh | bash
#      — or copy the file over and run: bash vm-setup.sh
#
# What it does:
#   - Installs Docker + Docker Compose plugin
#   - Clones the repo into DEPLOY_PATH
#   - Copies your .env file into place (you supply it interactively)
#   - Pulls images and starts all services

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
REPO_URL="${REPO_URL:-git@github.com:YOUR_ORG/wildleague-backend.git}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/wildleague/backend}"
DEPLOY_USER="${DEPLOY_USER:-$(whoami)}"
# ─────────────────────────────────────────────────────────────────────────────

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# ── 1. Install Docker ─────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  info "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$DEPLOY_USER"
  info "Docker installed. You may need to log out and back in for group changes to take effect."
else
  info "Docker already installed: $(docker --version)"
fi

# Verify Compose plugin
if ! docker compose version &>/dev/null; then
  error "Docker Compose plugin not found. Install it: https://docs.docker.com/compose/install/"
fi
info "Docker Compose: $(docker compose version)"

# ── 2. Clone the repository ───────────────────────────────────────────────────
if [ -d "$DEPLOY_PATH/.git" ]; then
  info "Repo already exists at $DEPLOY_PATH, skipping clone."
else
  info "Cloning repo into $DEPLOY_PATH..."
  sudo mkdir -p "$(dirname "$DEPLOY_PATH")"
  sudo chown "$DEPLOY_USER":"$DEPLOY_USER" "$(dirname "$DEPLOY_PATH")"
  git clone "$REPO_URL" "$DEPLOY_PATH"
fi

# ── 3. Set up the .env file ───────────────────────────────────────────────────
if [ ! -f "$DEPLOY_PATH/.env" ]; then
  if [ -f "$DEPLOY_PATH/.env.example" ]; then
    cp "$DEPLOY_PATH/.env.example" "$DEPLOY_PATH/.env"
    info ".env created from .env.example — edit it now before continuing:"
    info "  nano $DEPLOY_PATH/.env"
    read -r -p "Press ENTER once you have filled in $DEPLOY_PATH/.env ..."
  else
    error ".env not found and no .env.example exists. Create $DEPLOY_PATH/.env manually and re-run."
  fi
else
  info ".env already exists."
fi

# ── 4. Initial build & start ──────────────────────────────────────────────────
info "Building images and starting services..."
cd "$DEPLOY_PATH"
docker compose up --build -d

info "Running database migrations..."
docker compose exec -T api python manage.py migrate --noinput

info ""
info "Setup complete. Services running:"
docker compose ps
