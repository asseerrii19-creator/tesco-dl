#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -r requirements.txt
export APP_ENV=development
export APP_SECRET='TSCO-local-review-2026-change-before-shared-use'
export DATABASE_URL='sqlite:///./app/data/tsco_platform.db'
export SEED_DEMO_DATA=true
export SHOW_DEMO_ACCOUNTS=false
export BOOTSTRAP_ADMIN_EMAIL='admin@tsco.local'
export BOOTSTRAP_ADMIN_NAME='System Administrator'
export BOOTSTRAP_ADMIN_PASSWORD='Demo123!'
export REQUIRE_BOOTSTRAP_PASSWORD_CHANGE=false
export LMS_MODE=mock
export ENABLE_API_DOCS=true
if command -v open >/dev/null 2>&1; then (sleep 2; open http://127.0.0.1:8000 >/dev/null 2>&1 || true) & fi
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
