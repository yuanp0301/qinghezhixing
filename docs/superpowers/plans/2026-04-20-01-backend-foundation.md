# Plan 1 / 5 — Backend Foundation 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭好 FastAPI 后端骨架，具备配置、日志、PostgreSQL、Redis、会话鉴权、用户与角色、管理员用户 CRUD、审计日志，并带可运行的测试与 docker-compose 开发环境。

**Architecture:** 单体 FastAPI 应用（`app/`）。层次分明：`api/` 路由 → `services/` 业务 → `models/` ORM。配置集中在 `app/config.py`。鉴权用服务端 session（Redis 存 session，HttpOnly cookie）。数据库迁移走 Alembic。测试用 pytest + 本地 PG（docker-compose）。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic, Redis (redis-py async), pydantic-settings, passlib[bcrypt], pytest + pytest-asyncio + httpx, ruff + mypy.

**Spec 引用:**
- 设计文档：`docs/superpowers/specs/2026-04-20-knowledge-viz-site-design.md` 第 4/6/7 节
- PRD：`docs/superpowers/specs/2026-04-20-knowledge-viz-site-prd.md` §1 登录页、§8.2 用户管理

---

## 文件结构

Backend 仓库根就是项目根（`.` 下新建子目录）。前端在 plan 4 里放到 `frontend/`。

```
.
├── pyproject.toml              # 依赖、工具配置
├── .python-version             # 3.11
├── .env.example                # 配置示例
├── .gitignore
├── README.md
├── docker-compose.yml          # 本地 PG + Redis
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app 工厂
│   ├── config.py               # Settings（pydantic-settings）
│   ├── logging_conf.py         # 日志配置
│   ├── db.py                   # async engine / session
│   ├── redis_conn.py           # Redis 异步客户端
│   ├── deps.py                 # 依赖：db session、current_user、require_role
│   ├── security/
│   │   ├── __init__.py
│   │   ├── passwords.py        # bcrypt 哈希
│   │   └── sessions.py         # Redis 会话存取
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py             # DeclarativeBase
│   │   ├── user.py
│   │   └── audit_log.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   └── common.py           # 通用 Page/Error
│   ├── services/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── audit.py
│   └── api/
│       ├── __init__.py
│       ├── health.py           # /health
│       ├── auth.py             # /api/auth/*
│       └── admin_users.py      # /api/admin/users/*
└── tests/
    ├── conftest.py             # pytest 夹具：db、redis、client
    ├── test_health.py
    ├── test_auth.py
    └── test_admin_users.py
```

每个文件只承担一件事：`config.py` 只读环境、`db.py` 只管连接、`security/sessions.py` 只处理 session cookie、`services/*` 只放业务、`api/*` 只做路由和校验。

---

### Task 1: 仓库初始化与开发依赖

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1: 创建 `.python-version`**

```
3.11
```

- [ ] **Step 2: 创建 `pyproject.toml`**

```toml
[project]
name = "qinghe-zhixing"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "sqlalchemy>=2.0.28",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "redis>=5.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.9",
    "structlog>=24.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.1",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "ruff>=0.3",
    "mypy>=1.9",
    "types-passlib",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-ra -q"
testpaths = ["tests"]
```

- [ ] **Step 3: 创建 `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
.ruff_cache/
.mypy_cache/
htmlcov/
.coverage
dist/
build/
```

- [ ] **Step 4: 创建 `.env.example`**

```
APP_ENV=dev
APP_SECRET_KEY=please-change-me-32chars-min
DATABASE_URL=postgresql+asyncpg://qinghe:qinghe@localhost:5432/qinghe
REDIS_URL=redis://localhost:6379/0
SESSION_COOKIE_NAME=qh_session
SESSION_TTL_SECONDS=43200
LOG_LEVEL=INFO
```

- [ ] **Step 5: 创建 `README.md`**

```markdown
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
```

- [ ] **Step 6: 提交**

```bash
git init
git add .
git commit -m "chore: bootstrap repo with pyproject and env scaffolding"
```

---

### Task 2: docker-compose 本地依赖

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: 写 `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: qinghe
      POSTGRES_PASSWORD: qinghe
      POSTGRES_DB: qinghe
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U qinghe"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pg_data:
```

- [ ] **Step 2: 启动并验证**

Run: `docker compose up -d && docker compose ps`
Expected: `postgres` 和 `redis` 两项都是 `healthy`（等 10 秒）。

- [ ] **Step 3: 提交**

```bash
git add docker-compose.yml
git commit -m "chore: add local postgres and redis via docker compose"
```

---

### Task 3: 配置加载（Settings）

**Files:**
- Create: `app/__init__.py`（空）
- Create: `app/config.py`
- Create: `tests/__init__.py`（空）
- Create: `tests/test_config.py`

- [ ] **Step 1: 写失败的测试 `tests/test_config.py`**

```python
import os
from app.config import Settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_SECRET_KEY", "x" * 32)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@h:5432/d",
    )
    monkeypatch.setenv("REDIS_URL", "redis://h:6379/0")
    s = Settings()
    assert s.app_env == "test"
    assert s.session_cookie_name == "qh_session"
    assert s.session_ttl_seconds == 43200


def test_settings_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "short")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@h:5432/d",
    )
    monkeypatch.setenv("REDIS_URL", "redis://h:6379/0")
    try:
        Settings()
    except Exception as e:
        assert "at least 32" in str(e)
    else:
        raise AssertionError("expected validation error")
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/test_config.py -v`
Expected: ImportError（`app.config` 不存在）

- [ ] **Step 3: 写 `app/__init__.py` 与 `app/config.py`**

`app/__init__.py`：空文件。

`app/config.py`：

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_secret_key: str
    database_url: str
    redis_url: str

    session_cookie_name: str = "qh_session"
    session_ttl_seconds: int = 43200  # 12h
    log_level: str = "INFO"

    @field_validator("app_secret_key")
    @classmethod
    def secret_long_enough(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("APP_SECRET_KEY must be at least 32 characters")
        return v


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 4: 测试通过**

Run: `pytest tests/test_config.py -v`
Expected: 2 passed。

- [ ] **Step 5: 提交**

```bash
git add app/ tests/
git commit -m "feat(config): load settings from env with validation"
```

---

### Task 4: 日志配置

**Files:**
- Create: `app/logging_conf.py`
- Create: `tests/test_logging.py`

- [ ] **Step 1: 写测试**

```python
import logging
from app.logging_conf import configure_logging


def test_configure_logging_sets_level():
    configure_logging("DEBUG")
    assert logging.getLogger("app").level == logging.DEBUG
```

- [ ] **Step 2: 确认失败**

Run: `pytest tests/test_logging.py -v`
Expected: ImportError。

- [ ] **Step 3: 实现**

`app/logging_conf.py`：

```python
import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    )
    root.addHandler(handler)
    root.setLevel(level.upper())
    logging.getLogger("app").setLevel(level.upper())
```

- [ ] **Step 4: 测试通过**

Run: `pytest tests/test_logging.py -v`
Expected: 1 passed。

- [ ] **Step 5: 提交**

```bash
git add app/logging_conf.py tests/test_logging.py
git commit -m "feat(logging): add simple stdout logging configurator"
```

---

### Task 5: 数据库连接（async engine）

**Files:**
- Create: `app/db.py`
- Create: `app/models/__init__.py`（空）
- Create: `app/models/base.py`

- [ ] **Step 1: 实现 `app/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 2: 实现 `app/db.py`**

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    future=True,
)

SessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 3: 冒烟连接测试**

Run:

```bash
python -c "import asyncio; from app.db import engine; \
async def ping():
    async with engine.connect() as c:
        r = await c.exec_driver_sql('select 1');
        print(r.scalar())
asyncio.run(ping())"
```

Expected: 输出 `1`。

- [ ] **Step 4: 提交**

```bash
git add app/db.py app/models/
git commit -m "feat(db): add async engine and session factory"
```

---

### Task 6: Alembic 初始化

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`（官方模板原样）
- Create: `alembic/versions/.keep`

- [ ] **Step 1: 生成骨架**

Run: `alembic init -t async alembic`
Expected: 生成 `alembic/` 目录 + `alembic.ini`。

- [ ] **Step 2: 修改 `alembic.ini`**

- 注释掉 `sqlalchemy.url = ...`（由 env.py 动态读取）。

- [ ] **Step 3: 替换 `alembic/env.py`**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from app.config import get_settings
from app.models.base import Base
# 后续 plan 2/3 会在此导入更多模型，以填充 metadata
from app.models import user as _user  # noqa: F401
from app.models import audit_log as _audit  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: 提交（models 暂未存在，Step 5 再补迁移）**

```bash
git add alembic.ini alembic/
git commit -m "chore(alembic): initialize async migration scaffold"
```

---

### Task 7: users 与 audit_logs 模型 + 首次迁移

**Files:**
- Create: `app/models/user.py`
- Create: `app/models/audit_log.py`
- Create: `alembic/versions/0001_initial.py`

- [ ] **Step 1: `app/models/user.py`**

```python
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'active'")
    )
    note: Mapped[str | None] = mapped_column(String(200))
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin','creator','viewer')", name="ck_users_role"
        ),
        CheckConstraint(
            "status IN ('active','disabled')", name="ck_users_status"
        ),
    )
```

- [ ] **Step 2: `app/models/audit_log.py`**

```python
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
```

- [ ] **Step 3: 生成迁移**

Run: `alembic revision --autogenerate -m "initial users and audit_logs"`
Expected: 在 `alembic/versions/` 生成文件，内含 `users`、`audit_logs` 两表。把文件名重命名为 `0001_initial.py`（保留 revision id）。

- [ ] **Step 4: 应用迁移**

Run: `alembic upgrade head`
Expected: 命令无报错，`psql` 查 `\dt` 应看到两张表。

- [ ] **Step 5: 提交**

```bash
git add app/models/ alembic/versions/
git commit -m "feat(db): add users and audit_logs tables with initial migration"
```

---

### Task 8: 密码哈希

**Files:**
- Create: `app/security/__init__.py`（空）
- Create: `app/security/passwords.py`
- Create: `tests/test_passwords.py`

- [ ] **Step 1: 写测试**

```python
from app.security.passwords import hash_password, verify_password


def test_hash_and_verify():
    h = hash_password("Secret123!")
    assert h != "Secret123!"
    assert verify_password("Secret123!", h) is True
    assert verify_password("wrong", h) is False


def test_hash_is_salted():
    a = hash_password("same")
    b = hash_password("same")
    assert a != b
```

- [ ] **Step 2: 确认失败**

Run: `pytest tests/test_passwords.py -v`
Expected: ImportError。

- [ ] **Step 3: 实现**

```python
from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _ctx.verify(plain, hashed)
```

- [ ] **Step 4: 测试通过**

Run: `pytest tests/test_passwords.py -v`
Expected: 2 passed。

- [ ] **Step 5: 提交**

```bash
git add app/security/ tests/test_passwords.py
git commit -m "feat(security): add bcrypt password hashing"
```

---

### Task 9: Redis 会话存取

**Files:**
- Create: `app/redis_conn.py`
- Create: `app/security/sessions.py`
- Create: `tests/test_sessions.py`

- [ ] **Step 1: `app/redis_conn.py`**

```python
from redis.asyncio import Redis

from app.config import get_settings

_settings = get_settings()

redis: Redis = Redis.from_url(
    _settings.redis_url, decode_responses=True
)
```

- [ ] **Step 2: 写测试 `tests/test_sessions.py`**

```python
import pytest

from app.security.sessions import (
    create_session,
    get_session,
    delete_session,
)


@pytest.mark.asyncio
async def test_session_roundtrip():
    sid = await create_session(user_id=42, ttl_seconds=60)
    assert sid and len(sid) >= 32
    data = await get_session(sid)
    assert data == {"user_id": 42}
    await delete_session(sid)
    assert await get_session(sid) is None


@pytest.mark.asyncio
async def test_missing_session_returns_none():
    assert await get_session("nope") is None
```

- [ ] **Step 3: 确认失败**

Run: `pytest tests/test_sessions.py -v`
Expected: ImportError。

- [ ] **Step 4: 实现 `app/security/sessions.py`**

```python
import json
import secrets

from app.redis_conn import redis

_PREFIX = "sess:"


async def create_session(user_id: int, ttl_seconds: int) -> str:
    sid = secrets.token_urlsafe(32)
    await redis.set(
        _PREFIX + sid,
        json.dumps({"user_id": user_id}),
        ex=ttl_seconds,
    )
    return sid


async def get_session(sid: str) -> dict | None:
    raw = await redis.get(_PREFIX + sid)
    return json.loads(raw) if raw else None


async def delete_session(sid: str) -> None:
    await redis.delete(_PREFIX + sid)


async def touch_session(sid: str, ttl_seconds: int) -> None:
    await redis.expire(_PREFIX + sid, ttl_seconds)
```

- [ ] **Step 5: 测试通过**

Run: `pytest tests/test_sessions.py -v`
Expected: 2 passed（确保 docker 里 redis 在运行）。

- [ ] **Step 6: 提交**

```bash
git add app/redis_conn.py app/security/sessions.py tests/test_sessions.py
git commit -m "feat(security): redis-backed session store"
```

---

### Task 10: FastAPI 应用工厂与 /health

**Files:**
- Create: `app/main.py`
- Create: `app/api/__init__.py`（空）
- Create: `app/api/health.py`
- Create: `tests/conftest.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: `app/api/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 2: `app/main.py`**

```python
from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import get_settings
from app.logging_conf import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="青禾知行 API", version="0.1.0")
    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 3: `tests/conftest.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
```

- [ ] **Step 4: `tests/test_health.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 5: 运行**

Run: `pytest tests/test_health.py -v`
Expected: 1 passed。

- [ ] **Step 6: 手动验证**

Run: `uvicorn app.main:app --port 8000` 后 `curl localhost:8000/health`
Expected: `{"status":"ok"}`。

- [ ] **Step 7: 提交**

```bash
git add app/main.py app/api/ tests/conftest.py tests/test_health.py
git commit -m "feat(api): add FastAPI app factory and /health endpoint"
```

---

### Task 11: 测试数据库隔离（事务回滚夹具）

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/test_db_fixture.py`

- [ ] **Step 1: 改 `tests/conftest.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, engine
from app.main import app
from app.models.base import Base


@pytest.fixture(scope="session", autouse=True)
async def _prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db() -> AsyncSession:
    async with SessionLocal() as s:
        yield s
        await s.rollback()


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
```

> 说明：测试直接用开发库表结构；每个用例的 `db` 夹具回滚自身写入；跨用例隔离靠每个测试在夹具里清理自建数据，或使用独立 DB（v1 简化）。如担心污染，改为 `DATABASE_URL_TEST` 单独库即可。

- [ ] **Step 2: 加一个冒烟用例 `tests/test_db_fixture.py`**

```python
import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_db_connects(db):
    r = await db.execute(text("select 1"))
    assert r.scalar() == 1
```

- [ ] **Step 3: 运行**

Run: `pytest -v`
Expected: 全部通过。

- [ ] **Step 4: 提交**

```bash
git add tests/
git commit -m "test: add db session fixture with rollback isolation"
```

---

### Task 12: 依赖注入（current_user / require_role）

**Files:**
- Create: `app/deps.py`

- [ ] **Step 1: 写 `app/deps.py`**

```python
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionLocal
from app.models.user import User
from app.security.sessions import get_session, touch_session

settings = get_settings()


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        yield s


async def get_current_user(
    qh_session: Annotated[str | None, Cookie(alias="qh_session")] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not qh_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    data = await get_session(qh_session)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session expired")
    user = await db.get(User, data["user_id"])
    if not user or user.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user inactive")
    await touch_session(qh_session, settings.session_ttl_seconds)
    return user


def require_role(*roles: str):
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
        return user

    return _dep
```

- [ ] **Step 2: 提交（测试在下一任务联动）**

```bash
git add app/deps.py
git commit -m "feat(auth): add current_user and require_role dependencies"
```

---

### Task 13: Auth schemas 与 users service

**Files:**
- Create: `app/schemas/__init__.py`（空）
- Create: `app/schemas/common.py`
- Create: `app/schemas/auth.py`
- Create: `app/schemas/user.py`
- Create: `app/services/__init__.py`（空）
- Create: `app/services/users.py`
- Create: `app/services/audit.py`
- Create: `tests/test_users_service.py`

- [ ] **Step 1: `app/schemas/common.py`**

```python
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
```

- [ ] **Step 2: `app/schemas/auth.py`**

```python
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=8, max_length=64)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    status: str

    class Config:
        from_attributes = True


class LoginOut(BaseModel):
    user: UserOut
```

- [ ] **Step 3: `app/schemas/user.py`**

```python
import re

from pydantic import BaseModel, Field, field_validator

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{2,32}$")


class UserCreateIn(BaseModel):
    username: str
    password: str = Field(min_length=8, max_length=64)
    role: str = Field(pattern=r"^(admin|creator|viewer)$")
    note: str | None = Field(default=None, max_length=200)

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError(
                "username must be 2-32 chars of [A-Za-z0-9_]"
            )
        return v

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if not (
            any(c.isalpha() for c in v) and any(c.isdigit() for c in v)
        ):
            raise ValueError(
                "password must contain letters and digits"
            )
        return v


class UserUpdateIn(BaseModel):
    role: str | None = Field(default=None, pattern=r"^(admin|creator|viewer)$")
    status: str | None = Field(default=None, pattern=r"^(active|disabled)$")
    note: str | None = Field(default=None, max_length=200)


class UserAdminOut(BaseModel):
    id: int
    username: str
    role: str
    status: str
    note: str | None
    last_login_at: str | None = None
    created_at: str

    class Config:
        from_attributes = True


class PasswordResetOut(BaseModel):
    new_password: str
```

- [ ] **Step 4: `app/services/audit.py`**

```python
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def write_audit(
    db: AsyncSession,
    *,
    actor_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )
```

> 说明：不 commit，交由调用方事务边界。

- [ ] **Step 5: `app/services/users.py`**

```python
import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreateIn, UserUpdateIn
from app.security.passwords import hash_password


def _random_password(n: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    # Ensure at least 1 letter + 1 digit.
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(n))
        if any(c.isalpha() for c in pw) and any(c.isdigit() for c in pw):
            return pw


async def get_by_username(
    db: AsyncSession, username: str
) -> User | None:
    q = select(User).where(User.username == username)
    return (await db.execute(q)).scalar_one_or_none()


async def create_user(
    db: AsyncSession, data: UserCreateIn
) -> User:
    exists = await get_by_username(db, data.username)
    if exists:
        raise ValueError("username taken")
    u = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
        note=data.note,
    )
    db.add(u)
    await db.flush()
    return u


async def update_user(
    db: AsyncSession, user_id: int, data: UserUpdateIn
) -> User:
    u = await db.get(User, user_id)
    if not u:
        raise LookupError("user not found")
    if data.role is not None:
        u.role = data.role
    if data.status is not None:
        u.status = data.status
    if data.note is not None:
        u.note = data.note
    await db.flush()
    return u


async def reset_password(
    db: AsyncSession, user_id: int
) -> str:
    u = await db.get(User, user_id)
    if not u:
        raise LookupError("user not found")
    new = _random_password(12)
    u.password_hash = hash_password(new)
    await db.flush()
    return new


async def list_users(
    db: AsyncSession,
    *,
    q: str | None,
    role: str | None,
    status_: str | None,
    page: int,
    size: int,
) -> tuple[list[User], int]:
    stmt = select(User)
    count_stmt = select(func.count(User.id))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(User.username.ilike(pattern))
        count_stmt = count_stmt.where(User.username.ilike(pattern))
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    if status_:
        stmt = stmt.where(User.status == status_)
        count_stmt = count_stmt.where(User.status == status_)
    stmt = (
        stmt.order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()
    return list(rows), total
```

- [ ] **Step 6: 测试 `tests/test_users_service.py`**

```python
import pytest

from app.schemas.user import UserCreateIn, UserUpdateIn
from app.services import users as svc


@pytest.mark.asyncio
async def test_create_update_reset(db):
    u = await svc.create_user(
        db,
        UserCreateIn(
            username="alice1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    assert u.id and u.status == "active"

    u2 = await svc.update_user(
        db, u.id, UserUpdateIn(role="creator", status="disabled")
    )
    assert u2.role == "creator" and u2.status == "disabled"

    new_pw = await svc.reset_password(db, u.id)
    assert len(new_pw) == 12
    assert any(c.isalpha() for c in new_pw)
    assert any(c.isdigit() for c in new_pw)


@pytest.mark.asyncio
async def test_duplicate_username(db):
    await svc.create_user(
        db,
        UserCreateIn(
            username="dupe1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    with pytest.raises(ValueError):
        await svc.create_user(
            db,
            UserCreateIn(
                username="dupe1",
                password="Passw0rd!",
                role="viewer",
            ),
        )
```

- [ ] **Step 7: 运行**

Run: `pytest tests/test_users_service.py -v`
Expected: 2 passed。

- [ ] **Step 8: 提交**

```bash
git add app/schemas/ app/services/ tests/test_users_service.py
git commit -m "feat(users): schemas, service, audit helper"
```

---

### Task 14: Auth API（/api/auth/login, logout, me）

**Files:**
- Create: `app/api/auth.py`
- Modify: `app/main.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: 写测试 `tests/test_auth.py`**

```python
import pytest

from app.schemas.user import UserCreateIn
from app.services import users as svc


@pytest.mark.asyncio
async def test_login_logout_me(client, db):
    await svc.create_user(
        db,
        UserCreateIn(
            username="bob1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    await db.commit()

    r = await client.post(
        "/api/auth/login",
        json={"username": "bob1", "password": "Passw0rd!"},
    )
    assert r.status_code == 200
    assert r.cookies.get("qh_session")

    r2 = await client.get("/api/auth/me")
    assert r2.status_code == 200
    assert r2.json()["username"] == "bob1"

    r3 = await client.post("/api/auth/logout")
    assert r3.status_code == 204

    r4 = await client.get("/api/auth/me")
    assert r4.status_code == 401


@pytest.mark.asyncio
async def test_login_wrong_password(client, db):
    await svc.create_user(
        db,
        UserCreateIn(
            username="carol1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    await db.commit()
    r = await client.post(
        "/api/auth/login",
        json={"username": "carol1", "password": "nope12345"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_disabled(client, db):
    u = await svc.create_user(
        db,
        UserCreateIn(
            username="dan1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    u.status = "disabled"
    await db.commit()
    r = await client.post(
        "/api/auth/login",
        json={"username": "dan1", "password": "Passw0rd!"},
    )
    assert r.status_code == 403
```

- [ ] **Step 2: 实现 `app/api/auth.py`**

```python
from datetime import datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import LoginIn, LoginOut, UserOut
from app.security.passwords import verify_password
from app.security.sessions import create_session, delete_session
from app.services.audit import write_audit
from app.services.users import get_by_username

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(resp: Response, sid: str) -> None:
    resp.set_cookie(
        settings.session_cookie_name,
        sid,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.app_env != "dev",
        path="/",
    )


@router.post("/login", response_model=LoginOut)
async def login(
    data: LoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginOut:
    user = await get_by_username(db, data.username)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid credentials"
        )
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account disabled")

    sid = await create_session(user.id, settings.session_ttl_seconds)
    _set_cookie(response, sid)
    user.last_login_at = datetime.utcnow()
    await write_audit(
        db, actor_id=user.id, action="login",
        target_type="user", target_id=user.id,
    )
    await db.commit()
    return LoginOut(user=UserOut.model_validate(user))


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    qh_session: str | None = Cookie(default=None, alias="qh_session"),
) -> Response:
    if qh_session:
        await delete_session(qh_session)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
```

- [ ] **Step 3: 挂到 `app/main.py`**

改 `create_app` 中加：

```python
from app.api.auth import router as auth_router
...
app.include_router(auth_router)
```

- [ ] **Step 4: 运行**

Run: `pytest tests/test_auth.py -v`
Expected: 3 passed。

- [ ] **Step 5: 提交**

```bash
git add app/api/auth.py app/main.py tests/test_auth.py
git commit -m "feat(auth): login, logout, me endpoints with session cookie"
```

---

### Task 15: 管理员用户 API（/api/admin/users）

**Files:**
- Create: `app/api/admin_users.py`
- Modify: `app/main.py`
- Create: `tests/test_admin_users.py`

- [ ] **Step 1: 写测试**

```python
import pytest

from app.schemas.user import UserCreateIn
from app.services import users as svc


async def _login(client, db, username, role="admin"):
    await svc.create_user(
        db,
        UserCreateIn(
            username=username,
            password="Passw0rd!",
            role=role,
        ),
    )
    await db.commit()
    r = await client.post(
        "/api/auth/login",
        json={"username": username, "password": "Passw0rd!"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_create_and_list(client, db):
    await _login(client, db, "admin1", "admin")

    r = await client.post(
        "/api/admin/users",
        json={
            "username": "newone1",
            "password": "Initial12",
            "role": "creator",
        },
    )
    assert r.status_code == 201
    assert r.json()["username"] == "newone1"

    r2 = await client.get("/api/admin/users?page=1&size=20")
    assert r2.status_code == 200
    assert r2.json()["total"] >= 2


@pytest.mark.asyncio
async def test_non_admin_forbidden(client, db):
    await _login(client, db, "creator1", "creator")
    r = await client.get("/api/admin/users")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_reset_password(client, db):
    await _login(client, db, "admin2", "admin")
    r = await client.post(
        "/api/admin/users",
        json={
            "username": "resetme1",
            "password": "Initial12",
            "role": "viewer",
        },
    )
    uid = r.json()["id"]
    r2 = await client.post(f"/api/admin/users/{uid}/reset-password")
    assert r2.status_code == 200
    assert len(r2.json()["new_password"]) == 12
```

- [ ] **Step 2: 实现 `app/api/admin_users.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import (
    PasswordResetOut,
    UserAdminOut,
    UserCreateIn,
    UserUpdateIn,
)
from app.services import users as svc
from app.services.audit import write_audit

router = APIRouter(
    prefix="/api/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_role("admin"))],
)


def _out(u: User) -> UserAdminOut:
    return UserAdminOut(
        id=u.id,
        username=u.username,
        role=u.role,
        status=u.status,
        note=u.note,
        last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        created_at=u.created_at.isoformat(),
    )


@router.get("", response_model=Page[UserAdminOut])
async def list_users(
    q: str | None = None,
    role: str | None = None,
    status_: str | None = Query(default=None, alias="status"),
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
) -> Page[UserAdminOut]:
    rows, total = await svc.list_users(
        db, q=q, role=role, status_=status_, page=page, size=size
    )
    return Page[UserAdminOut](
        items=[_out(r) for r in rows],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=UserAdminOut, status_code=201)
async def create_user(
    data: UserCreateIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
) -> UserAdminOut:
    try:
        u = await svc.create_user(db, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    await write_audit(
        db, actor_id=actor.id, action="user.create",
        target_type="user", target_id=u.id,
        detail={"username": u.username, "role": u.role},
    )
    await db.commit()
    return _out(u)


@router.patch("/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: int,
    data: UserUpdateIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
) -> UserAdminOut:
    try:
        u = await svc.update_user(db, user_id, data)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    await write_audit(
        db, actor_id=actor.id, action="user.update",
        target_type="user", target_id=u.id,
        detail=data.model_dump(exclude_none=True),
    )
    await db.commit()
    return _out(u)


@router.post(
    "/{user_id}/reset-password", response_model=PasswordResetOut
)
async def reset_password(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
) -> PasswordResetOut:
    try:
        new = await svc.reset_password(db, user_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    await write_audit(
        db, actor_id=actor.id, action="user.reset_password",
        target_type="user", target_id=user_id,
    )
    await db.commit()
    return PasswordResetOut(new_password=new)
```

- [ ] **Step 3: 挂到 `app/main.py`**

```python
from app.api.admin_users import router as admin_users_router
...
app.include_router(admin_users_router)
```

- [ ] **Step 4: 运行**

Run: `pytest tests/test_admin_users.py -v`
Expected: 3 passed。

- [ ] **Step 5: 提交**

```bash
git add app/api/admin_users.py app/main.py tests/test_admin_users.py
git commit -m "feat(admin): user CRUD endpoints with RBAC and audit"
```

---

### Task 16: 首个管理员 seed 命令

**Files:**
- Create: `app/cli/__init__.py`（空）
- Create: `app/cli/seed_admin.py`

- [ ] **Step 1: 实现 `app/cli/seed_admin.py`**

```python
"""Create or reset the initial admin account.

Usage:
    python -m app.cli.seed_admin <username> <password>
"""
import asyncio
import sys

from app.db import SessionLocal
from app.schemas.user import UserCreateIn
from app.services import users as svc
from app.security.passwords import hash_password


async def _main(username: str, password: str) -> None:
    async with SessionLocal() as db:
        existing = await svc.get_by_username(db, username)
        if existing:
            existing.password_hash = hash_password(password)
            existing.role = "admin"
            existing.status = "active"
            print(f"reset existing user {username} as admin")
        else:
            await svc.create_user(
                db,
                UserCreateIn(
                    username=username,
                    password=password,
                    role="admin",
                ),
            )
            print(f"created admin user {username}")
        await db.commit()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    asyncio.run(_main(sys.argv[1], sys.argv[2]))
```

- [ ] **Step 2: 运行一次**

Run: `python -m app.cli.seed_admin root Abcdef12`
Expected: 输出 `created admin user root`；再跑一次输出 `reset existing user root as admin`。

- [ ] **Step 3: 提交**

```bash
git add app/cli/
git commit -m "feat(cli): seed initial admin user"
```

---

### Task 17: 根路由与 OpenAPI 冒烟

**Files:**
- Modify: `tests/test_health.py`

- [ ] **Step 1: 加一个 openapi 用例**

```python
@pytest.mark.asyncio
async def test_openapi_contains_auth(client):
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/api/auth/login" in paths
    assert "/api/admin/users" in paths
```

- [ ] **Step 2: 运行全部测试**

Run: `pytest -v`
Expected: 所有用例通过。

- [ ] **Step 3: 提交**

```bash
git add tests/test_health.py
git commit -m "test: assert auth and admin-users routes exposed via openapi"
```

---

### Task 18: README 补齐启动步骤

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 把 README 换成**

```markdown
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
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: document first-run and endpoints"
```

---

## Self-Review 结果

- 覆盖范围：设计 §4（users / audit_logs）、§6.6（会话）、§7（FastAPI/PG/Redis）；PRD §1 登录页后端、§8.2 用户管理后端全部纳入。Contents/Shares 由 plan 2/3 承接，不在本计划范围——这是有意的。
- 无占位符："implement later" / TBD 均未出现；每个步骤都有可运行代码或命令。
- 命名一致：`get_current_user` / `require_role` 在 `deps.py` 定义后，Task 14/15 使用；`SessionLocal` 统一来自 `app/db.py`；`settings.session_cookie_name` 定义后在 auth 和 deps 两处一致使用。
- TDD：每个有逻辑的任务（8/9/13/14/15）都是"先测试、再实现、再跑通"。

---

## 交付清单

结束后应当存在：

- docker-compose（PG + Redis）可起。
- `alembic upgrade head` 建两张表。
- `python -m app.cli.seed_admin` 创建首个 admin。
- `uvicorn app.main:app` 正常启动，访问 `/health`、`/api/auth/login`、`/api/admin/users` 功能正确。
- `pytest` 全绿。
