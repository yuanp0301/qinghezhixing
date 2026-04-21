# 青禾知行

知识可视化站点后端（v1）。

## 开发

1. `cp .env.example .env`
2. `docker compose up -d`
3. `pip install -e ".[dev]"`
4. `alembic upgrade head`
5. `uvicorn app.main:app --reload`

## 测试

`pytest`
