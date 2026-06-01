from typing import Any
from pydantic import BaseModel

class AIQuestion(BaseModel):
    user_id: str
    question: str

class AIResponse(AIQuestion):
    answer: str

class ChatHistoryRequest(BaseModel):
    user_id: str

class ChatHistoryMessage(BaseModel):
    role: str
    text: str
    offers: list[Any] | None = None

class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryMessage]
