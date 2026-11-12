#!/usr/bin/env bash
set -euo pipefail

cd /workspace

# 前端依赖
if [ -f frontend/package-lock.json ]; then
  (cd frontend && npm ci)
else
  (cd frontend && npm install)
fi

# 提醒准备 .env
if [ ! -f .env ]; then
  echo ""
  echo "⚠️  未找到 .env。请执行："
  echo "    cp .env.example .env"
  echo "    然后填入 APP_PASSWORD_HASH / APP_SECRET_KEY / ANTHROPIC_API_KEY"
  echo ""
fi

echo "✅ dev container ready"