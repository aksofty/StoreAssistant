from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system_setting import SystemSetting
from app.database import AsyncSessionLocal


async def get_setting(session: AsyncSession, key: str) -> SystemSetting | None:
    result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
    return result.scalar_one_or_none()


async def get_str_setting(key: str, default: str) -> int:
    async with AsyncSessionLocal() as session:
        setting = await get_setting(session, key)
    if setting is None:
        return default
    try:
        return str(setting.value)
    except (ValueError, TypeError):
        return default

async def get_int_setting(key: str, default: int) -> int:
    async with AsyncSessionLocal() as session:
        setting = await get_setting(session, key)
    if setting is None:
        return default
    try:
        return int(setting.value)
    except (ValueError, TypeError):
        return default


async def get_float_setting(key: str, default: float) -> float:
    async with AsyncSessionLocal() as session:
        setting = await get_setting(session, key)
    if setting is None:
        return default
    try:
        return float(setting.value)
    except (ValueError, TypeError):
        return default
