from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app.config import Config

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # ВАЖНО: Здесь должна быть ваша проверка пароля (например, из БД)
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            request.session.update({"token": "secret-token"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        return True