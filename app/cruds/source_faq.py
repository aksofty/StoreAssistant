from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.source_faq import SourceFaq

async def get_faq_sources(
        session: AsyncSession, active=True) -> list[SourceFaq]:

    query = (
        select(SourceFaq)
        .where(SourceFaq.active == active)
        .order_by(SourceFaq.id.asc())
    )
    result = await session.execute(query)
    return result.scalars().all()