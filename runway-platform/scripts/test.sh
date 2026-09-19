#!/usr/bin/env bash
# 一键运行全部测试（后端 pytest + 前端 vitest + 前端构建）
set -euo pipefail
cd "$(dirname "$0")/.."

echo "===== 后端测试 ====="
cd backend
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
python -m pytest -v

echo "===== 前端测试与构建 ====="
cd ../frontend
if [ ! -d "node_modules" ]; then
  npm install
fi
npm test
npm run build

echo "✓ 全部测试通过，前端构建成功"
