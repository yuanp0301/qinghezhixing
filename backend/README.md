# 青禾知行 · 后端（v1）

## 首次启动

1. 复制环境变量：`cp .env.example .env`
2. 起依赖：`docker compose up -d`
3. 安装：`pip install -e ".[dev]"`
4. 迁移：`alembic upgrade head`
5. 建管理员：`python -m app.cli.seed_admin root 'ChangeMe1'`
6. 运行：`uvicorn app.main:app --reload`

## 测试

`pytest`

## 路由概览

- `GET /health`
- `POST /api/auth/login` / `POST /api/auth/logout` / `GET /api/auth/me`
- `GET/POST/PATCH /api/admin/users`（仅 admin）
- `POST /api/admin/users/{id}/reset-password`

后续 plan 在此补 contents、tags、shares。
