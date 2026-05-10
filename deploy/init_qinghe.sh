#!/usr/bin/env bash
# ECS 裸机：Git 工作副本 + SQLite + Nginx + systemd
# 密钥与密码仅放在 init_qinghe.env（切勿入库），见 init_qinghe.env.example
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${INIT_QINGHE_ENV:-$SCRIPT_DIR/init_qinghe.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: 未找到配置文件: $ENV_FILE"
  echo "请执行: cp $SCRIPT_DIR/init_qinghe.env.example $ENV_FILE && chmod 600 $ENV_FILE"
  echo "（或通过环境变量 INIT_QINGHE_ENV 指定路径）"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${APP_DIR:?请在 $ENV_FILE 中设置 APP_DIR（项目 clone 根目录）}"
: "${PUBLIC_BASE_URL:?请在 $ENV_FILE 中设置 PUBLIC_BASE_URL}"
: "${ADMIN_PASS:?请在 $ENV_FILE 中设置 ADMIN_PASS}"
: "${OSS_BUCKET:?请在 $ENV_FILE 中设置 OSS_BUCKET}"
: "${OSS_ACCESS_KEY_ID:?请在 $ENV_FILE 中设置 OSS_ACCESS_KEY_ID}"
: "${OSS_ACCESS_KEY_SECRET:?请在 $ENV_FILE 中设置 OSS_ACCESS_KEY_SECRET}"
: "${OSS_ENDPOINT:?请在 $ENV_FILE 中设置 OSS_ENDPOINT}"
: "${OSS_REGION:?请在 $ENV_FILE 中设置 OSS_REGION}"

BACKEND_DIR="${BACKEND_DIR:-$APP_DIR/backend}"
FRONTEND_DIR="${FRONTEND_DIR:-$APP_DIR/frontend}"
SERVICE_NAME="${SERVICE_NAME:-qinghe-backend}"
RUN_USER="${RUN_USER:-www-data}"
RUN_GROUP="${RUN_GROUP:-www-data}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
ADMIN_USER="${ADMIN_USER:-root}"
OSS_INTERNAL_ENDPOINT="${OSS_INTERNAL_ENDPOINT:-}"

if [[ ! -d "$BACKEND_DIR" || ! -d "$FRONTEND_DIR" ]]; then
  echo "ERROR: 后端或前端目录不存在: BACKEND_DIR=$BACKEND_DIR FRONTEND_DIR=$FRONTEND_DIR"
  exit 1
fi

echo "[1/8] 安装系统依赖..."
if command -v yum >/dev/null 2>&1; then
  yum install -y git nginx sqlite
  yum install -y python3.11 2>/dev/null || true
  if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
    yum install -y nodejs
  fi
elif command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git nginx sqlite3 curl python3.11 python3.11-venv python3.11-dev
  if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
  fi
else
  echo "ERROR: 不支持的包管理器（需要 yum 或 apt-get）"
  exit 1
fi

PYBIN="$(command -v python3.11 || true)"
if [[ -z "$PYBIN" ]]; then
  echo "ERROR: 未找到 python3.11。请先安装 Python 3.11（见 deploy/ECS部署指南.md）后再运行本脚本。"
  exit 1
fi
if ! "$PYBIN" -c 'import sys; assert sys.version_info[:2] == (3, 11)' 2>/dev/null; then
  echo "ERROR: 需要 Python 3.11.x，当前: $($PYBIN --version)"
  exit 1
fi

echo "[2/8] 确保运行用户存在..."
if ! id -u "$RUN_USER" >/dev/null 2>&1; then
  useradd -r -s /sbin/nologin "$RUN_USER"
fi

echo "[3/8] 初始化后端虚拟环境与依赖（requirements.txt）..."
cd "$BACKEND_DIR"
"$PYBIN" -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt

_write_backend_env() {
  APP_SECRET_KEY="$1"
  export APP_SECRET_KEY
  export BACKEND_DIR
  python <<'PY'
import os
from pathlib import Path

def esc_line(key: str, val: str) -> str:
    if val == "":
        return f"{key}="
    if val.strip() != val or any(c in val for c in ('"', "\\", "\n", "#")):
        escaped = (
            val.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )
        return f'{key}="{escaped}"'
    return f"{key}={val}"

backend = Path(os.environ["BACKEND_DIR"])
secret = os.environ["APP_SECRET_KEY"]
oss_id = os.environ["OSS_ACCESS_KEY_ID"]
oss_secret = os.environ["OSS_ACCESS_KEY_SECRET"]
lines = [
    esc_line("APP_ENV", "prod"),
    esc_line("APP_SECRET_KEY", secret),
    esc_line("DATABASE_URL", "sqlite+aiosqlite:///./data/qinghe.db"),
    esc_line("SESSION_COOKIE_NAME", os.environ.get("SESSION_COOKIE_NAME", "qh_session")),
    esc_line("SESSION_TTL_SECONDS", os.environ.get("SESSION_TTL_SECONDS", "604800")),
    esc_line(
        "SESSION_COOKIE_SAMESITE",
        os.environ.get("SESSION_COOKIE_SAMESITE", "lax"),
    ),
    esc_line("LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO")),
    esc_line("OSS_ENDPOINT", os.environ["OSS_ENDPOINT"]),
    esc_line("OSS_INTERNAL_ENDPOINT", os.environ.get("OSS_INTERNAL_ENDPOINT", "")),
    esc_line("OSS_BUCKET", os.environ["OSS_BUCKET"]),
    esc_line("OSS_ACCESS_KEY_ID", oss_id),
    esc_line("OSS_ACCESS_KEY_SECRET", oss_secret),
    esc_line("OSS_REGION", os.environ["OSS_REGION"]),
    esc_line("UPLOAD_MAX_BYTES", os.environ.get("UPLOAD_MAX_BYTES", "10485760")),
    esc_line("SHARE_MIN_SECONDS", os.environ.get("SHARE_MIN_SECONDS", "300")),
    esc_line("SHARE_MAX_SECONDS", os.environ.get("SHARE_MAX_SECONDS", "2592000")),
    esc_line(
        "SHARE_DEFAULT_SECONDS",
        os.environ.get("SHARE_DEFAULT_SECONDS", "86400"),
    ),
    esc_line("PUBLIC_BASE_URL", os.environ["PUBLIC_BASE_URL"]),
]
cors = os.environ.get("CORS_ORIGINS", "").strip()
if cors:
    lines.append(esc_line("CORS_ORIGINS", cors))

(backend / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

echo "[4/8] 写入后端 .env（SQLite）..."
if [[ ! -f "$BACKEND_DIR/.env.example" ]]; then
  echo "WARN: 未找到 .env.example，仅写入运行所需变量"
fi
APP_SECRET_KEY="$(python -c "import secrets; print(secrets.token_urlsafe(48))")"
_write_backend_env "$APP_SECRET_KEY"

mkdir -p "$BACKEND_DIR/data"
chown -R "$RUN_USER":"$RUN_GROUP" "$BACKEND_DIR/data"
chmod 755 "$BACKEND_DIR/data"

echo "[5/8] 初始化数据库与管理员..."
sudo -u "$RUN_USER" -g "$RUN_GROUP" bash -lc "
  set -e
  cd '$BACKEND_DIR' && source venv/bin/activate && \
  alembic upgrade head && \
  python -m app.cli.seed_admin $(printf '%q' "$ADMIN_USER") $(printf '%q' "$ADMIN_PASS")
"

echo "[6/8] 构建前端..."
cd "$FRONTEND_DIR"
npm install
npm run build

echo "[7/8] 写入 systemd 服务..."
cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Qinghe Backend
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$BACKEND_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$BACKEND_DIR/venv/bin/uvicorn app.main:app --host $BACKEND_HOST --port $BACKEND_PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo "[8/8] 写入 Nginx 配置..."
cat >/etc/nginx/conf.d/qinghe.conf <<EOF
server {
    listen 80;
    server_name _;
    root $FRONTEND_DIR/dist;
    index index.html;
    location / {
        try_files \$uri \$uri/ /index.html;
    }
    location /api/ {
        proxy_pass http://$BACKEND_HOST:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
    location /s/ { proxy_pass http://$BACKEND_HOST:$BACKEND_PORT; }
    location /d/ { proxy_pass http://$BACKEND_HOST:$BACKEND_PORT; }
    location /view/ { proxy_pass http://$BACKEND_HOST:$BACKEND_PORT; }
    location /view-share/ { proxy_pass http://$BACKEND_HOST:$BACKEND_PORT; }
}
EOF
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "========================================"
echo "初始化完成"
echo "后端: systemctl status $SERVICE_NAME --no-pager"
echo "健康检查: curl -fsS http://127.0.0.1:$BACKEND_PORT/health"
echo "管理员用户: $ADMIN_USER （密码为您在 init_qinghe.env 中设置的 ADMIN_PASS）"
echo "========================================"
