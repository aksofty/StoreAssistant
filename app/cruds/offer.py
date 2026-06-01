from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence
from app.models.offer import Offer
from sqlalchemy.dialects.sqlite import insert


def _prepare_offer(item: dict) -> dict:
    return {
        "offer_id": str(item.get("offer_id", "")),
        "available": bool(item.get("available", True)),
        "name": item.get("name", ""),
        "price": float(item.get("price") or 0),
        "url": item.get("url"),
        "category": item.get("category"),
        "vendor": item.get("vendor"),
        "vendor_code": item.get("vendor_code"),
        "description": (item.get("description") or "")[:1024],
        "picture": item.get("picture"),
        "params": item.get("params") or {},
        "source_id": item.get("source_id"),
    }


async def sync_offers(
    session: AsyncSession,
    catalog: list[dict],
) -> dict[str, list[str]]:
    if not catalog:
        return {"added": [], "deleted": []}

    incoming_ids: set[str] = {str(item["offer_id"]) for item in catalog}

    # Все offer_id, которые уже есть в БД (глобально, без привязки к источнику)
    existing_ids: set[str] = set(
        (await session.execute(select(Offer.offer_id))).scalars()
    )

    added_ids = list(incoming_ids - existing_ids)
    deleted_ids = list(existing_ids - incoming_ids)

    # Upsert: при конфликте по offer_id — обновляем все поля кроме PK
    stmt = insert(Offer)
    update_dict = {
        col.name: stmt.excluded[col.name]
        for col in Offer.__table__.columns
        if col.name not in ["id", "offer_id"]
    }
    await session.execute(
        stmt.on_conflict_do_update(index_elements=[Offer.offer_id], set_=update_dict),
        [_prepare_offer(item) for item in catalog],
    )

    # Удаляем офферы, которых нет ни в одном источнике
    if deleted_ids:
        await session.execute(
            delete(Offer).where(Offer.offer_id.in_(deleted_ids))
        )

    await session.commit()

    return {"added": added_ids, "deleted": deleted_ids}

async def get_offers(
    session: AsyncSession, available=True) -> list[Offer]:
    query = (
        select(Offer)
        .where(Offer.available == available)
        .order_by(Offer.id.asc())
        )
    result = await session.execute(query)
    return result.scalars().all()


async def get_offers_by_ids(session: AsyncSession, offer_ids: list[str]) -> Sequence[Offer]:
    """Выбирает из базы данных все товары, чьи offer_id есть в переданном списке."""
    # Если список пустой, сразу возвращаем пустой результат, не делая запрос в БД
    if not offer_ids:
        return []
        
    # Формируем SQL-запрос: SELECT * FROM offers WHERE offer_id IN (...)
    query = select(Offer).where(Offer.offer_id.in_(offer_ids))
    
    # Выполняем запрос
    result = await session.execute(query)
    
    # Извлекаем чистые объекты модели (scalar)
    return result.scalars().all()