from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.source_yml import SourceYml

async def get_yml_sources(
        session: AsyncSession, active=True) -> list[SourceYml]:

    query = (
        select(SourceYml)
        .where(SourceYml.active == active)
        .order_by(SourceYml.id.asc())
    )
    result = await session.execute(query)
    return result.scalars().all()