#!/usr/bin/env bash
# 一键启动：构建镜像并启动 PostgreSQL + 后端（含前端静态页面）
set -euo pipefail

cd "$(dirname "$0")"

if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
  else
    echo "✗ 未找到 docker compose / docker-compose，请先安装 Docker。" >&2
    exit 1
  fi

  echo "▶ 使用 Docker 启动（PostgreSQL + API + 前端页面）..."
  $DC up -d --build

  echo "▶ 等待服务就绪..."
  for i in $(seq 1 30); do
    if curl -fs http://localhost:8000/health >/dev/null 2>&1; then
      echo ""
      echo "✓ 启动完成"
      echo "  平台地址 : http://localhost:8000"
      echo "  API 文档 : http://localhost:8000/docs"
      echo "  停止服务 : $DC down        （清除数据加 -v）"
      exit 0
    fi
    sleep 2
  done
  echo "✗ 服务未在预期时间内就绪，请查看日志：$DC logs api" >&2
  exit 1
else
  echo "ℹ 未检测到 Docker，改用本地开发模式（SQLite）启动。"
  exec ./scripts/dev.sh
fi
