from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.faq_extra import FaqExtra


async def get_faq_extras(session: AsyncSession) -> list[FaqExtra]:
    result = await session.execute(select(FaqExtra))
    return list(result.scalars().all())


async def get_faq_extras_by_ids(session: AsyncSession, ids: list[int]) -> list[FaqExtra]:
    result = await session.execute(select(FaqExtra).where(FaqExtra.id.in_(ids)))
    return list(result.scalars().all())
