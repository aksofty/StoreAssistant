from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.source_faq import SourceFaq


class Faq(Base):
    __tablename__ = 'faq'
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column()
    answer: Mapped[str] = mapped_column()

    source_id: Mapped[int] = mapped_column(ForeignKey("source_faq.id"))
    source: Mapped["SourceFaq"] = relationship()
