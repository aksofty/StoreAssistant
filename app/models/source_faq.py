from typing import Any, Dict
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.models.source_base import SourceBase


class SourceFaq(SourceBase, Base):
    __tablename__ = "source_faq"

    selector_question: Mapped[str] = mapped_column(nullable=True)
    selector_answer: Mapped[str] = mapped_column(nullable=True)
