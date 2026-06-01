import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqladmin import Admin
import uvicorn
from app import CLIENT_LOG_FILE
from app.admin.admin_auth import AdminAuth
from app.admin.views import (
    BotUserAdmin,
    BotUserMessageAdmin,
    ChatAssistantAdmin,
    SourceFaqAdmin,
    SourceYmlAdmin,
    SystemSettingAdmin,
)
from app.config import Config
from app.database import engine
from app.lifespan import lifespan
from app.routers import ask

logger.remove()
logger.add(sys.stdout, level="DEBUG")
logger.add(CLIENT_LOG_FILE, rotation="1 MB")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

app.include_router(ask.router)
app.mount("/static", StaticFiles(directory="static"), name="static")

authentication_backend = AdminAuth(secret_key=Config.ADMIN_SECRET_KEY)
admin = Admin(app, engine, authentication_backend=authentication_backend)

for view in [
    ChatAssistantAdmin,
    BotUserMessageAdmin,
    SystemSettingAdmin,
    SourceYmlAdmin,
    SourceFaqAdmin,
    BotUserAdmin
]:
    admin.add_view(view)


def main():
    logger.info("Starting application...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        reload_includes=["*.md"],
    )


if __name__ == "__main__":
    main()
