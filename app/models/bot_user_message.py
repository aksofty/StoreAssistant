import enum
from sqlalchemy import Enum, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from datetime import datetime

class MessageType(enum.Enum):
    SYSTEM  = "SystemMessage"
    HUMAN   = "HumanMessage"
    AI      = "AIMessage"
    TOOL    = "ToolMessage"


class BotUserMessage(Base):
    __tablename__ = 'bot_users_messages'

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("bot_users.chat_id"))
    
    type: Mapped[MessageType] = mapped_column(Enum(MessageType), default=MessageType.HUMAN)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    tokens: Mapped[int] = mapped_column(default=0)



