 #!/usr/bin/env bash\
set -euo pipefail

# ====== 可改参数（按需修改）======
APP_DIR="/var/www/qinghezhixing"\
BACKEND_DIR="$APP_DIR/backend"\
FRONTEND_DIR="$APP_DIR/frontend"\
SERVICE_NAME="qinghe-backend"\
RUN_USER="www-data"         # CentOS 常见可改为 nginx
RUN_GROUP="www-data"        # CentOS 常见可改为 nginx
BACKEND_HOST="127.0.0.1"\
BACKEND_PORT="8000"\
PUBLIC_BASE_URL="https://qinghe.school"   # YOUR_DOMAIN_OR_IP
ADMIN_USER="root"\
ADMIN_PASS='ChangeMe_2026!'                   # 必改强密码
# OSS
OSS_ENDPOINT="oss-cn-shanghai.aliyuncs.com"\
OSS_BUCKET="ss-pai-5txvgrigv5i1khj4ij-cn-shanghai"\
OSS_ACCESS_KEY_ID=LTAI5t9ptwqWejRESwtWkFAq\
OSS_ACCESS_KEY_SECRET=NxxqGyu4cmH0hREPn6LK7OqTmuSenV\
OSS_REGION="cn-shanghai"

# ====== 检查目录 ======
if [[ ! -d "$BACKEND_DIR" || ! -d "$FRONTEND_DIR" ]]; then
  echo "ERROR: 项目目录不存在：$APP_DIR"
  exit 1
fi
echo "[1/8] 安装系统依赖..."
if command -v yum >/dev/null 2>&1; then
  yum install -y git nginx python3 python3-pip python3-venv sqlite
  # node 可选，若无再装
  if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
    yum install -y nodejs
  fi
elif command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git nginx python3 python3-pip python3-venv sqlite3 curl
  if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
  fi
else
  echo "ERROR: 不支持的包管理器"
  exit 1
fi
echo "[2/8] 确保运行用户存在..."
if ! id -u "$RUN_USER" >/dev/null 2>&1; then
  useradd -r -s /sbin/nologin "$RUN_USER"
fi
echo "[3/8] 初始化后端虚拟环境与依赖..."
cd "$BACKEND_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
echo "[4/8] 写入后端 .env（SQLite）..."
cp -f .env.example .env
cat > .env <<EOF
APP_ENV=prod
APP_SECRET_KEY=$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)
DATABASE_URL=sqlite+aiosqlite:///./data/qinghe.db
SESSION_COOKIE_NAME=qh_session
SESSION_TTL_SECONDS=604800
LOG_LEVEL=INFO
OSS_ENDPOINT=$OSS_ENDPOINT
OSS_INTERNAL_ENDPOINT=
OSS_BUCKET=$OSS_BUCKET
OSS_ACCESS_KEY_ID=$OSS_ACCESS_KEY_ID
OSS_ACCESS_KEY_SECRET=$OSS_ACCESS_KEY_SECRET
OSS_REGION=$OSS_REGION
UPLOAD_MAX_BYTES=10485760
SHARE_MIN_SECONDS=300
SHARE_MAX_SECONDS=2592000
SHARE_DEFAULT_SECONDS=86400
PUBLIC_BASE_URL=$PUBLIC_BASE_URL
EOF
mkdir -p data
chown -R "$RUN_USER":"$RUN_GROUP" data
chmod 755 data
echo "[5/8] 初始化数据库与管理员..."
# 用运行用户执行，避免后续权限问题
sudo -u "$RUN_USER" -g "$RUN_GROUP" bash -lc "
  cd '$BACKEND_DIR' && \
  source venv/bin/activate && \
  alembic stamp base && \
  alembic upgrade head && \
  python -m app.cli.seed_admin '$ADMIN_USER' '$ADMIN_PASS'
"
echo "[6/8] 构建前端..."
cd "$FRONTEND_DIR"
npm install
npm run build
echo "[7/8] 写入 systemd 服务..."
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
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
cat > /etc/nginx/conf.d/qinghe.conf <<EOF
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
echo "后端服务状态: systemctl status $SERVICE_NAME --no-pager"
echo "健康检查: curl http://127.0.0.1:$BACKEND_PORT/health"
echo "管理员账号: $ADMIN_USER"
echo "管理员密码: $ADMIN_PASS"
echo "========================================"