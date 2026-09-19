#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# 机场跑道占用冲突预演平台 —— 一键启动脚本
#
# 用法:
#   ./start.sh                使用 Docker Compose 启动（推荐）
#   ./start.sh --local        本机直接运行（无需 Docker，需要 Python3 / Node）
#   ./start.sh --test         运行全部后端 + 前端测试
#   ./start.sh --stop         停止 Docker 服务
#   ./start.sh --reset        清空数据库卷并重新启动
# -----------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}▶${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

run_tests() {
  info "运行后端测试 ..."
  (
    cd "$ROOT/backend"
    if [ ! -d .venv ]; then
      python3 -m venv --without-pip .venv
      . .venv/bin/activate
      curl -sSL https://bootstrap.pypa.io/get-pip.py | python -
    else
      . .venv/bin/activate
    fi
    pip install -q -r requirements.txt
    python -m pytest tests/ -q
  )
  info "运行前端测试 ..."
  (
    cd "$ROOT/frontend"
    [ -d node_modules ] || npm install
    npm test
  )
  ok "全部测试通过"
}

start_docker() {
  command -v docker >/dev/null || { warn "未检测到 Docker，请使用 ./start.sh --local"; exit 1; }
  info "构建并启动 PostgreSQL / 后端 / 前端 容器 ..."
  compose up -d --build
  info "等待后端就绪 ..."
  for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/api/health >/dev/null; then
      ok "后端已就绪"
      break
    fi
    sleep 2
  done
  echo
  ok "启动完成："
  echo "    前端控制台 : http://localhost:8080"
  echo "    后端 API   : http://localhost:8000  （文档 /docs）"
  echo "    PostgreSQL : localhost:5432 (runway/runway)"
  echo
  info "查看日志: docker compose logs -f    停止: ./start.sh --stop"
}

stop_docker() {
  info "停止服务 ..."
  compose down
  ok "已停止"
}

reset_docker() {
  info "删除容器与数据库卷 ..."
  compose down -v
  start_docker
}

start_local() {
  command -v python3 >/dev/null || { warn "需要 Python 3.11+"; exit 1; }
  command -v node >/dev/null || { warn "需要 Node 18+"; exit 1; }

  info "准备后端虚拟环境 ..."
  (
    cd "$ROOT/backend"
    if [ ! -d .venv ]; then
      python3 -m venv --without-pip .venv
      . .venv/bin/activate
      if ! python -m pip --version >/dev/null 2>&1; then
        curl -sSL https://bootstrap.pypa.io/get-pip.py | python -
      fi
      pip install -r requirements.txt
    fi
  )

  info "安装前端依赖 ..."
  ( cd "$ROOT/frontend" && [ -d node_modules ] || npm install )

  DB="$ROOT/backend/runway-local.db"
  rm -f "$DB"

  info "启动 FastAPI（SQLite: $DB）..."
  (
    cd "$ROOT/backend"
    DATABASE_URL="sqlite:///$DB" .venv/bin/python -m uvicorn app.main:app \
      --host 127.0.0.1 --port 8000
  ) &
  BACK_PID=$!

  info "启动 Vite 开发服务器 ..."
  ( cd "$ROOT/frontend" && npx vite --host 127.0.0.1 --port 5173 ) &
  FRONT_PID=$!

  trap 'echo; info "停止本地服务 ..."; kill $BACK_PID $FRONT_PID 2>/dev/null || true' EXIT
  echo
  ok "本地启动完成："
  echo "    前端控制台 : http://localhost:5173"
  echo "    后端 API   : http://localhost:8000  （文档 /docs）"
  echo
  wait
}

case "${1:---docker}" in
  --docker|"") start_docker ;;
  --local)     start_local ;;
  --test)      run_tests ;;
  --stop)      stop_docker ;;
  --reset)     reset_docker ;;
  *)
    echo "用法: $0 [--docker|--local|--test|--stop|--reset]"
    exit 1
    ;;
esac
