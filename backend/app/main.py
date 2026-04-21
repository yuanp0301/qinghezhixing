from fastapi import FastAPI

from app.api.admin_users import router as admin_users_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.config import get_settings
from app.logging_conf import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="青禾知行 API", version="0.1.0")
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(admin_users_router)
    return app


app = create_app()
