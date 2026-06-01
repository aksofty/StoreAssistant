from typing import Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bot_user import BotUser

async def get_add_bot_user(session: AsyncSession, chat_id: str, name: str = None) -> BotUser:
    #async with AsyncSessionLocal() as session:
    user = await get_bot_user_by_chatid(session, chat_id)
    if user:
        return user
    else:
        return await add_bot_user(session, chat_id=chat_id, name=name)

async def get_bot_user_by_chatid(session: AsyncSession, chat_id: str) -> BotUser:
    query = select(BotUser).where(BotUser.chat_id == chat_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def add_bot_user(session: AsyncSession, **user_data) -> Optional[BotUser]:
    new_user = BotUser(**user_data)
    session.add(new_user)
    try:
        await session.commit()
        await session.refresh(new_user)
        return new_user
    except IntegrityError as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        await session.rollback()
        return None