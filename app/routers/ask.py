
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from loguru import logger

from app.assistants.store_assistant import StoreAssistant
from app.config import Config
from app.cruds.bot_user import get_add_bot_user
from app.cruds.bot_user_message import can_user_ask, get_message_history, user_ask_limit
from app.cruds.system_setting import get_float_setting, get_int_setting
from app.database import AsyncSessionLocal
from app.models.bot_user_message import MessageType
from app.schemas.ask import AIQuestion, AIResponse, ChatHistoryMessage, ChatHistoryRequest, ChatHistoryResponse
from app.utils.common import normalize_answer

_LOCAL_IPS = {"127.0.0.1", "::1", "localhost"}




def check_access(request: Request, fast_api_key: Annotated[str | None, Header()] = None):
    client_ip = request.client.host if request.client else ""
    if client_ip in _LOCAL_IPS:
        return

    origin = request.headers.get("origin", "")
    if origin in Config.ALLOWED_ORIGINS:
        return

    if fast_api_key not in Config.FAST_API_SECRET_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")


def get_ai_assistant(request: Request) -> StoreAssistant:
    return request.app.state.assistant


_waiting_count = 0

router = APIRouter(tags=["AI Assistant"])

@router.post("/ask", response_model=AIResponse, dependencies=[Depends(check_access)])
async def ask_node(
    request: AIQuestion,
    http_request: Request,
    assistant: StoreAssistant = Depends(get_ai_assistant),
):
    global _waiting_count

    semaphore = http_request.app.state.gigachat_semaphore
    max_queue_size = http_request.app.state.max_queue_size

    if _waiting_count >= max_queue_size:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Сервер перегружен, попробуйте позже.",
        )

    _waiting_count += 1
    _semaphore_acquired = False
    try:
        async with semaphore:
            _semaphore_acquired = True
            _waiting_count -= 1

            async with AsyncSessionLocal() as session:
                delay = await get_float_setting("assistant.ask_delay", default=10)
                can_ask = await can_user_ask(session=session, chat_id=request.user_id, delay=delay)

                if not can_ask:
                    return AIResponse(
                        user_id=request.user_id,
                        question=request.question,
                        answer=json.dumps({"text": "Вы слишком часто задаете вопросы, подождите немного..."}, ensure_ascii=False),
                    )
                
                ask_interval = await get_float_setting("assistant.ask_interval", default=86400)
                ask_limit = await get_float_setting("assistant.ask_limit", default=10)
                user_limit = await user_ask_limit(session=session, chat_id=request.user_id, interval=ask_interval, limit=ask_limit)
                if user_limit:
                    return AIResponse(
                        user_id=request.user_id,
                        question=request.question,
                        answer=json.dumps({"text": "Вы слишком много задаете вопросов, давайте немного передохнем..."}, ensure_ascii=False),
                    )

                await get_add_bot_user(session, request.user_id, name="")

            response = await assistant.ask(query=request.question, chat_id=request.user_id)
            answer = normalize_answer(response) if response else json.dumps({"text": "Извините, какие-то проблемы."}, ensure_ascii=False)

            return AIResponse(
                user_id=request.user_id,
                question=request.question,
                answer=answer
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        if not _semaphore_acquired:
            _waiting_count -= 1


@router.post("/chat_history", response_model=ChatHistoryResponse, dependencies=[Depends(check_access)])
async def get_chat_history(request: ChatHistoryRequest):
    async with AsyncSessionLocal() as session:
        limit = await get_int_setting("history.count_chat_view", default=20)
        ttl_seconds = await get_int_setting("history.ttl_chat_view", default=216001)
        messages = await get_message_history(session, chat_id=request.user_id, limit=limit, ttl_seconds=ttl_seconds)

    result = []
    for msg in messages:
        if msg.type == MessageType.HUMAN:
            result.append(ChatHistoryMessage(role="user", text=msg.text))
        elif msg.type == MessageType.AI:
            normalized = normalize_answer(msg.text)
            try:
                data = json.loads(normalized)
                result.append(ChatHistoryMessage(
                    role="bot",
                    text=data.get("text", ""),
                    offers=data.get("offers") or None,
                ))
            except (json.JSONDecodeError, ValueError):
                result.append(ChatHistoryMessage(role="bot", text=msg.text))

    return ChatHistoryResponse(messages=result)
