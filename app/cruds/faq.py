from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.faq import Faq
from typing import Sequence

async def add_faq(
    session: AsyncSession,
    source_id: int,
    question: str,
    answer: list[str],
):
    """
    Добавляет новую запись в таблицу faq.
    """

    new_faq = Faq(
        source_id=source_id,
        question=question,
        answer=answer
    )
    
    session.add(new_faq)
    await session.commit()


async def add_faqs(
    session: AsyncSession,
    faq_list: list[dict],
    source_id: int = None
):
    """
    Массово добавляет новые записи в таблицу faq из списка словарей.
    каждый словарь должен содержать ключи: source_id, question, answer.
    """
    if not faq_list:
        return
    
    for item in faq_list:
        item["source_id"] = source_id

    # Выполняем массовую вставку (Bulk Insert)
    await session.execute(
        insert(Faq),
        faq_list
    )
    
    # Фиксируем изменения в базе данных
    # session.commit() ТУТ НЕ НУЖЕН, так как управление транзакцией 
    # происходит снаружи через контекстный менеджер session.begin()
    #await session.commit()


async def delete_faqs_by_source(session: AsyncSession, source_id: int):
    """
    Удаляет все записи из таблицы faq, связанные с конкретным источником source_id.
    """
    if source_id is None:
        logger.warning("Попытка удалить FAQ с source_id = None отменена.")
        return

    await session.execute(
        delete(Faq).where(Faq.source_id == source_id)
    )
    # session.commit() ТУТ НЕ НУЖЕН, так как управление транзакцией 
    # происходит снаружи через контекстный менеджер session.begin()


async def get_faqs(session: AsyncSession) -> list[Faq]:
    """Получает все записи из таблицы faq."""
    # Формируем SQL-запрос SELECT * FROM faq
    query = select(Faq)

    # Выполняем запрос
    result = await session.execute(query)

    # Извлекаем чистые объекты модели Faq из результата
    return result.scalars().all()

async def get_faqs_by_source_ids(session: AsyncSession, source_ids: list) -> Sequence[Faq]:
    """Выбирает все FAQ-записи по списку source_id."""
    if not source_ids:
        return []
    query = select(Faq).where(Faq.source_id.in_(source_ids))
    result = await session.execute(query)
    return result.scalars().all()


async def get_faqs_by_ids(session: AsyncSession, faq_ids: list[str]) -> Sequence[Faq]:
    """Выбирает из базы данных все товары, чьи offer_id есть в переданном списке."""
    # Если список пустой, сразу возвращаем пустой результат, не делая запрос в БД
    if not faq_ids:
        return []
        
    # Формируем SQL-запрос: SELECT * FROM offers WHERE offer_id IN (...)
    query = select(Faq).where(Faq.id.in_(faq_ids))
    
    # Выполняем запрос
    result = await session.execute(query)
    
    # Извлекаем чистые объекты модели (scalar)
    return result.scalars().all()