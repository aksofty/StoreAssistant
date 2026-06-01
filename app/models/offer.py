from typing import Any, Dict, Optional
from sqlalchemy import ForeignKey
from sqlalchemy.types import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.source_yml import SourceYml

class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[str] = mapped_column(unique=True)
    available: Mapped[bool] = mapped_column(default=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column()
    url: Mapped[Optional[str]] = mapped_column(String(255), default=None, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), default=None, nullable=True)
    vendor: Mapped[Optional[str]] = mapped_column(String(255), default=None, nullable=True)
    vendor_code: Mapped[Optional[str]] = mapped_column(String(255), default=None, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), default=None, nullable=True)
    picture: Mapped[Optional[str]] = mapped_column(String(255), default=None, nullable=True)
    params: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    source_id: Mapped[int] = mapped_column(ForeignKey("source_yml.id"), default=None, nullable=True)
    source: Mapped["SourceYml"] = relationship()