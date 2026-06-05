import json
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_gigachat import GigaChat
from loguru import logger
from app.cruds.bot_user_message import add_bot_user_message, get_message_history
from app.cruds.system_setting import get_float_setting, get_int_setting, get_str_setting
from app.database import AsyncSessionLocal
from app.models.bot_user_message import MessageType
from app.tools.tools import ALL_TOOLS, TOOLS_MAP
from app.utils.faiss import faiss_search


_MESSAGE_CLASS = {
    MessageType.HUMAN: HumanMessage,
    MessageType.AI: AIMessage,
    MessageType.TOOL: ToolMessage,
}

_NO_TOOLS_PROMPT = (
    "У тебя больше нет попыток вызова функций. "
    "Ответь пользователю прямо сейчас на основе полученной информации."
)

def _extract_text(raw: str) -> str:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "text" in parsed:
            return parsed["text"]
    except (json.JSONDecodeError, TypeError):
        pass
    return raw


class StoreAssistant:
    def __init__(
        self,
        offers_store=None,
        faqs_store=None,
        faqs_extra_store=None,
        embeddings=None,
        system_prompt: str = "",
        scope: str = "GIGACHAT_API_PERS",
        model: str = "GigaChat-2-Pro",
        temperature: float = 0.1,
        top_p: float = 0.1,
        max_tokens: int = 1024,
        max_score: int = 300,
        k: int = 3,
        history_count: int = 5,
        history_ttl: int = 14801,
        max_connections = 1

    ):
        self.offers_store = offers_store
        self.faqs_store = faqs_store
        self.faqs_extra_store = faqs_extra_store
        self.embeddings = embeddings
        self.system_prompt = system_prompt
        self.max_score = max_score
        self.k = k
        self.history_count = history_count
        self.history_ttl = history_ttl

        self.chat = GigaChat(
            model=model,
            temperature=temperature,
            top_p=top_p,
            verify_ssl_certs=False,
            scope=scope,
            max_tokens=max_tokens,
            http_client_parameters={"max_connections": max_connections},
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self.model_with_tools = self.chat.bind_tools(ALL_TOOLS)

    async def ask(self, query: str, chat_id: int) -> str:
        await self._get_settings()

        cleaned_query = query.strip().removesuffix("?").strip()
        history = await self._get_user_message_history(chat_id=chat_id, limit=self.history_count, ttl=self.history_ttl)

        system_prompt = self.system_prompt
        faqs = await faiss_search(
            query=cleaned_query,
            embeddings=self.embeddings,
            store=self.faqs_store,
            extra_store=self.faqs_extra_store,
            max_score=self.max_score,
            k=self.k
        )
        if faqs:
            system_prompt += f"\n**НАЧАЛО КОНТЕКСТА**:\n{'\n'.join(faqs)}\n**КОНЕЦ КОНТЕКСТА**"


        messages = [SystemMessage(content=system_prompt)] + history + [HumanMessage(content=cleaned_query)]
        response_text, tool_messages, total_tokens = await self._run_model_with_tools(messages)

        if response_text:
            await self._save_dialog(chat_id, cleaned_query, response_text, total_tokens)
            return response_text

        final = await self.chat.ainvoke(tool_messages + [HumanMessage(content=_NO_TOOLS_PROMPT)])
        total_tokens += self._get_total_tokens(final)
        await self._save_dialog(chat_id, cleaned_query, final.content, total_tokens)
        return final.content

    async def _save_dialog(self, chat_id: int, human_text: str, ai_text: str, tokens: int = 0) -> None:
        async with AsyncSessionLocal() as session:
            await add_bot_user_message(session, chat_id=chat_id, message_type=MessageType.HUMAN, text=human_text)
            await add_bot_user_message(session, chat_id=chat_id, message_type=MessageType.AI, text=ai_text, tokens=tokens)

    async def _run_model_with_tools(
        self, messages: list[BaseMessage], iter_nums: int = 3
    ) -> tuple[str | None, list[BaseMessage], int]:
        total_tokens = 0
        tool_messages = list(messages)

        for _ in range(iter_nums):
            response = await self.model_with_tools.ainvoke(tool_messages)
            total_tokens += self._get_total_tokens(response)

            if not response.tool_calls:
                return response.content, [], total_tokens

            tool_messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_to_call = TOOLS_MAP.get(tool_name)

                if tool_to_call:
                    logger.info(f"Вызов {tool_name} с аргументами {tool_call['args']}")
                    config = {"configurable": {"offers_store": self.offers_store}}
                    result = await tool_to_call.ainvoke(input=tool_call["args"], config=config)
                    tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
                else:
                    tool_messages.append(ToolMessage(content="Ошибка: Инструмент не найден.", tool_call_id=tool_call["id"]))

        return None, tool_messages, total_tokens

    async def _get_settings(self) -> None:
        self.chat.temperature = await get_float_setting("assistant.temperature", default=self.chat.temperature)
        self.chat.top_p = await get_float_setting("assistant.top_p", default=self.chat.top_p)
        self.chat.model = await get_str_setting("assistant.model", default=self.chat.model)
        self.chat.max_tokens = await get_str_setting("assistant.max_tokens", default=self.chat.max_tokens)

        prompt = await get_str_setting("assistant.prompt", default="")
        response_prompt = await get_str_setting("assistant.prompt_response_format", default="")
        self.system_prompt = f"{prompt}\n{response_prompt}"
        self.max_score = await get_int_setting("faiss.faq.max_score", default=self.max_score)
        self.k = await get_int_setting("faiss.faq.k", default=self.k)
        self.history_count = await get_int_setting("assistant.history_message_count", default=self.history_count)
        self.history_ttl = await get_int_setting("history.ttl_chat", default=self.history_ttl)

    def _get_total_tokens(self, response) -> int:
        if not response.response_metadata:
            return 0
        token_usage = response.response_metadata.get("token_usage") or {}
        return token_usage.get("total_tokens", 0)

    async def _get_user_message_history(self, chat_id: int, limit: int = 5, ttl: int = 14800) -> list[BaseMessage]:
        async with AsyncSessionLocal() as session:
            message_history = await get_message_history(session, chat_id=chat_id, limit=limit, ttl_seconds=ttl)

        if not message_history:
            return [
                HumanMessage(content="Ищу товар"),
                AIMessage(content="Мне нужно больше информации. Попробуем ещё раз."),
            ]

        return [
            _MESSAGE_CLASS.get(m.type, SystemMessage)(content=_extract_text(m.text))
            for m in message_history
        ]
