import re
from sqlalchemy.types import String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates
from app.models.base import Base


class SystemSetting(Base):
    __tablename__ = 'system_settings'

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=True)
    sort: Mapped[int] = mapped_column(nullable=False, default=0)

    @validates("key")
    def validate_key(self, _, value: str) -> str:
        value = value.lower()
        if not re.fullmatch(r"[a-z.]+", value):
            raise ValueError(f"key must contain only Latin letters and dots, got: {value!r}")
        return value
