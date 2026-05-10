# 青禾知行 · 后端（v1）

## 环境要求

Python **3.11**（与 `pyproject.toml` 中 `requires-python` 一致）。macOS 可用 Homebrew：`brew install python@3.11`。

## 首次启动

1. 复制环境变量：`cp .env.example .env`
2. 创建虚拟环境并启用（示例为 Homebrew 的 3.11，路径按本机调整）：
   - `python3.11 -m venv .venv`
   - `source .venv/bin/activate`
3. 安装：`pip install -e ".[dev]"`
4. 迁移：`alembic upgrade head`
5. 建管理员：`python -m app.cli.seed_admin root 'admin1234'`
6. 运行：`uvicorn app.main:app --reload`

## 测试

`pytest`

## 路由概览

- `GET /health`
- `POST /api/auth/login` / `POST /api/auth/logout` / `GET /api/auth/me`
- `GET/POST/PATCH /api/admin/users`（仅 admin）
- `POST /api/admin/users/{id}/reset-password`
- `POST /api/contents`（creator/admin，multipart 上传）
- `GET  /api/contents`（公开库）
- `GET  /api/contents/mine`（creator/admin）
- `GET  /api/contents/{id}` / `PATCH` / `DELETE`
- `GET  /view/{id}`（沙箱观看）
- `GET  /api/tags`
- `GET/POST/PATCH/DELETE /api/admin/tags` + `POST /api/admin/tags/{id}/merge`
- `GET  /api/contents/admin/all` / `POST /api/contents/{id}/restore`（admin）
- `POST   /api/contents/{id}/shares`（生成分发链接）
- `GET    /api/contents/{id}/shares`（本人或 admin）
- `DELETE /api/shares/{token}`（撤销）
- `GET    /api/shares/{token}/logs`
- `GET    /s/{token}`（站外入口，统一失效页）
- `GET    /view-share/{token}`（沙箱观看）
- `GET    /d/{token}`（下载，受 allow_download 控制）

分发链接访问不再做 Redis 限流，统一按 token 状态（有效/过期/撤销）返回结果。

后续 plan 在此补 shares。
