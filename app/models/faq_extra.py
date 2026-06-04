from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class FaqExtra(Base):
    __tablename__ = 'faq_extra'
    __table_args__ = {'sqlite_autoincrement': True}
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column()
    answer: Mapped[str] = mapped_column()