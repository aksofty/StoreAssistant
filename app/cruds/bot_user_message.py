from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import delete, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bot_user_message import BotUserMessage, MessageType


async def get_message_history(
        session: AsyncSession, chat_id: str, limit: int = 4, ttl_seconds: int = 3600) -> list[BotUserMessage]:

    time_threshold = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
    query = (
        select(BotUserMessage)
        .where(BotUserMessage.chat_id == chat_id, BotUserMessage.created_at >= time_threshold)
        .order_by(BotUserMessage.id.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    messages = result.scalars().all()
    return messages[::-1]  # Возвращаем в порядке от старых к новым


async def can_user_ask(session, chat_id: str, delay: int) -> bool:
    query = (
        select(BotUserMessage)
        .filter_by(chat_id=chat_id, type=MessageType.HUMAN)
        .order_by(desc(BotUserMessage.created_at))
        .limit(1)
    )
    
    result = await session.execute(query)
    last_message = result.scalar_one_or_none()

    if not last_message:
        return True

    # Используем UTC время для сравнения
    now = datetime.now(timezone.utc)
    
    # Если в БД объект naive (без TZ), принудительно ставим ему UTC
    last_msg_time = last_message.created_at
    if last_msg_time.tzinfo is None:
        last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)

    elapsed_time = (now - last_msg_time).total_seconds()

    return elapsed_time >= delay


async def user_ask_limit(session, chat_id: str, interval: int, limit: int) -> bool:
    # Запрашиваем ровно столько последних сообщений, сколько составляет наш лимит
    query = (
        select(BotUserMessage)
        .filter_by(chat_id=chat_id, type=MessageType.HUMAN)
        .order_by(desc(BotUserMessage.created_at))
        .limit(limit)
    )

    result = await session.execute(query)
    messages = list(result.scalars().all())

    # Если сообщений меньше, чем лимит, то пользователь точно ничего не превысил
    if len(messages) < limit:
        return False

    # Если сообщений набралось ровно на лимит, проверяем самое СТАРОЕ из них.
    # Так как сортировка была по убыванию (desc), самое старое будет последним в списке.
    oldest_message = messages[-1]
    
    now = datetime.now(timezone.utc)
    last_msg_time = oldest_message.created_at
    

    if last_msg_time.tzinfo is None:
        last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)

    elapsed_time = (now - last_msg_time).total_seconds()

    # Если с момента отправки самого старого сообщения прошло МЕНЬШЕ времени,
    # чем заданный интервал — значит, пользователь исчерпал свой лимит.
    print(elapsed_time, interval)

    return elapsed_time <= interval
    


async def delete_old_messages(session: AsyncSession, max_age_seconds: int = 604800) -> int:
    threshold = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    result = await session.execute(
        delete(BotUserMessage).where(BotUserMessage.created_at < threshold)
    )
    await session.commit()
    return result.rowcount


async def add_bot_user_message(
        session: AsyncSession, chat_id: str, message_type: MessageType, text: str, tokens: int = 0 ) -> Optional[BotUserMessage]:
    
    new_message = BotUserMessage(chat_id=chat_id, type=message_type, text=text, tokens=tokens)
    session.add(new_message)
    try:
        await session.commit()
        await session.refresh(new_message)
        return new_message
    except IntegrityError as e:
        print(f"Ошибка при добавлении сообщения: {e}")
        await session.rollback()
        return None