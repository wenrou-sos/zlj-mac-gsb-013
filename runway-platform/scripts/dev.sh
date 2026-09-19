#!/usr/bin/env bash
# 本地开发模式：后端(8000, SQLite) + 前端 Vite 热更新(5173)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ---- 后端 ----
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

export DATABASE_URL="${DATABASE_URL:-sqlite:///./runway.db}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

cleanup() { kill "$API_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# ---- 前端 ----
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
  npm install
fi
exec npm run dev
