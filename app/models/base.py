from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    def __repr__(self):
        name = getattr(self, "name", getattr(self, "url", "None"))
        return f"{self.id}: {name}"
