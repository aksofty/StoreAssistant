from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class BotUser(Base):
    __tablename__ = 'bot_users'
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()