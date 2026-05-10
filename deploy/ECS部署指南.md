# 青禾知行 · 阿里云 ECS 裸机部署指南（Python 3.11 + SQLite）

本文档适用于：**不使用 Docker**，在单台 ECS 上直接运行后端、前端静态资源与 Nginx。数据库为 **SQLite**，表结构由 **Alembic** 创建。

---

## 一、环境与目录约定

| 项目 | 说明 |
|------|------|
| Python | **3.11.x**（须与 `backend/requirements.txt` 一致） |
| 操作系统 | 常见：Alibaba Cloud Linux 3、Ubuntu 22.04/24.04、Rocky/AlmaLinux 8+ |
| 代码目录 | 下文以 `/var/www/qinghezhixing` 为例（即仓库克隆后的**项目根目录**） |
| 后端目录 | `/var/www/qinghezhixing/backend` |
| 前端目录 | `/var/www/qinghezhixing/frontend` |

**安装 Python 3.11（示例）**

- Ubuntu：`sudo apt update && sudo apt install -y python3.11 python3.11-venv python3.11-dev`
- 若发行版软件源无 3.11，请先安装官方或第三方提供的 3.11，再执行后续步骤；可用 `python3.11 --version` 确认。

---

## 二、数据库（SQLite）

### 1）数据库文件位置

| 配置项 | 默认取值 |
|--------|----------|
| 环境变量 `DATABASE_URL` | `sqlite+aiosqlite:///./data/qinghe.db` |
| 磁盘路径（相对 `backend` 目录） | `backend/data/qinghe.db` |
| WAL 文件（SQLite 自动生成） | `backend/data/qinghe.db-wal`、`qinghe.db-shm` |

部署前创建目录并保证运行后端服务的系统用户可读写：

```bash
sudo mkdir -p /var/www/qinghezhixing/backend/data
sudo chown -R www-data:www-data /var/www/qinghezhixing/backend/data   # 用户、组按实际修改
```

### 2）建表（迁移）

在 **`backend` 目录**下、已激活虚拟环境后执行：

```bash
cd /var/www/qinghezhixing/backend
source venv/bin/activate
alembic upgrade head
```

空库首次执行即可创建全部业务表；无需手动 SQL。

### 3）初始化管理员账号（默认值）

首次上线建议使用以下**默认管理员**（登录后台后请立即修改密码）：

| 字段 | 默认值 |
|------|--------|
| 用户名 | `root` |
| 密码 | `admin1234` |

创建或重置该账号：

```bash
cd /var/www/qinghezhixing/backend
source venv/bin/activate
python -m app.cli.seed_admin root admin1234
```

若用户已存在，该命令会将对应用户重置为 admin 并更新密码。

---

## 三、后端服务

### 1）依赖安装

```bash
cd /var/www/qinghezhixing/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 2）环境变量

复制示例并按实际填写 OSS、公网访问地址等：

```bash
cp .env.example .env
chmod 600 .env
```

生产环境必须设置至少：`APP_SECRET_KEY`（≥32 字符）、`DATABASE_URL`、`OSS_*`、`PUBLIC_BASE_URL` 等（参见 `backend/.env.example`）。

### 3）端口与进程

| 项目 | 默认值 |
|------|--------|
| 监听地址 | `127.0.0.1`（仅本机，由 Nginx 对外） |
| 监听端口 | **8000** |
| 启动命令 | `uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| 健康检查 | `GET http://127.0.0.1:8000/health` |

systemd 示例（用户、路径请按实际修改）：

```ini
[Unit]
Description=Qinghe Backend
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/qinghezhixing/backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/var/www/qinghezhixing/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now qinghe-backend
```

---

## 四、前端（静态资源）

### 1）构建

```bash
cd /var/www/qinghezhixing/frontend
npm install
npm run build
```

构建产物目录：**`frontend/dist/`**。

### 2）访问方式

- 浏览器访问 **Nginx 对外端口（通常为 80 或 443）**，由 Nginx 提供 `dist` 下的静态文件。
- 前端通过同域或配置的 **`PUBLIC_BASE_URL`** 调用后端 API（详见 `.env` 与 `CORS_ORIGINS`）。

---

## 五、Nginx 反向代理

假设：

- 前端静态根目录：`/var/www/qinghezhixing/frontend/dist`
- 后端：`127.0.0.1:8000`

HTTP（80）示例：

```nginx
server {
    listen 80;
    server_name _;

    root /var/www/qinghezhixing/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }

    location /s/   { proxy_pass http://127.0.0.1:8000; }
    location /d/   { proxy_pass http://127.0.0.1:8000; }
    location /view/        { proxy_pass http://127.0.0.1:8000; }
    location /view-share/  { proxy_pass http://127.0.0.1:8000; }

    client_max_body_size 12m;
}
```

写入例如 `/etc/nginx/conf.d/qinghe.conf` 后：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

HTTPS：在阿里云申请证书后，增加 `listen 443 ssl`、证书路径及（可选）将 HTTP 重定向到 HTTPS 即可。

---

## 六、一键初始化脚本（可选）

仓库提供 `deploy/init_qinghe.sh`：在填写 **`deploy/init_qinghe.env`**（由 `deploy/init_qinghe.env.example` 复制）后执行，可自动安装依赖、`alembic upgrade head`、默认管理员、前端构建与 systemd/Nginx 配置。脚本内依赖安装方式为 **`pip install -r backend/requirements.txt`**。

密钥与口令不要提交到 Git；`deploy/init_qinghe.env` 已列入 `.gitignore`。

---

## 七、版本更新（代码拉取后）

```bash
cd /var/www/qinghezhixing
git pull

cd backend && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart qinghe-backend

cd ../frontend && npm install && npm run build
sudo systemctl reload nginx
```

---

## 八、安全组与防火墙（阿里云控制台）

- 入方向开放：**80**（及 **443** 若启用 HTTPS）；**22** 建议仅运维 IP。
- 后端 **8000** 仅监听 `127.0.0.1` 时，无需在安全组对公网开放 8000。
