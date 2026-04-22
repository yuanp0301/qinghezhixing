#!/usr/bin/env bash
set -euo pipefail
HOST="${1:?usage: smoke.sh https://qinghe.example.com}"

echo "[1/4] /health"
curl -fsS "$HOST/health" | grep -q '"status":"ok"'

echo "[2/4] login admin"
COOKIE=$(mktemp)
curl -fsS -c "$COOKIE" -H 'content-type: application/json' \
  -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PWD\"}" \
  "$HOST/api/auth/login" >/dev/null
curl -fsS -b "$COOKIE" "$HOST/api/auth/me" | grep -q '"role":"admin"'

echo "[3/4] list contents"
curl -fsS -b "$COOKIE" "$HOST/api/contents?page=1&page_size=1" >/dev/null

echo "[4/4] invalid share token returns generic page"
curl -fsS "$HOST/s/zzzzzzzzzzzz" | grep -q '链接已失效'

echo "smoke OK"
