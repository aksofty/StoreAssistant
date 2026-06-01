import asyncio
import os
from typing import List

import aiofiles
from bs4 import BeautifulSoup
from langchain_gigachat import GigaChat
from pydantic import BaseModel, Field

from app.utils.html_cleaner import HTMLCleaner


class _FaqItem(BaseModel):
    """Пара вопрос-ответ."""
    question: str = Field(description="Вопрос пользователя")
    answer: str = Field(description="Развёрнутый ответ на вопрос")


class _FaqList(BaseModel):
    """Список пар вопрос-ответ, извлечённых из текста."""
    items: List[_FaqItem] = Field(description="Список пар вопрос-ответ")


_SYSTEM_PROMPT = (
    "Ты — эксперт по подготовке данных для базы знаний. "
    "Из предоставленного текста извлеки все смысловые пары вопрос-ответ. "
    "Каждый вопрос должен отражать конкретную потребность пользователя, "
    "а ответ — исчерпывающе отвечать на него, сохраняя все цифры, условия и детали. "
    "Если текст не содержит полезной информации для FAQ — верни пустой список."
)


async def _extract_faqs_from_chunk(chunk: str, llm: GigaChat) -> list:
    structured_llm = llm.with_structured_output(_FaqList)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"ТЕКСТ:\n{chunk}"},
    ]
    try:
        result: _FaqList = await structured_llm.ainvoke(messages)
        return [{"question": item.question, "answer": item.answer} for item in result.items]
    except Exception:
        return []


async def create_faqs_from_html(file_path: str, credentials: str = None, selector: str = None) -> list:
    result = await HTMLCleaner.process(file_path, selector=selector)
    chunks: list = result.get("page_content", [])
    if not chunks:
        return []

    llm = GigaChat(
        credentials=credentials,
        model="GigaChat-2",
        verify_ssl_certs=False,
        temperature=0.1,
        top_p=0.1,
    )

    results = await asyncio.gather(*[_extract_faqs_from_chunk(chunk, llm) for chunk in chunks])
    return [faq for chunk_faqs in results for faq in chunk_faqs]


async def parse_faq_html(
    file_path: str,
    question_selector: str = None,
    answer_selector: str = None,
    credentials: str = None
) -> list:
    if not file_path:
        return []
    
    if not question_selector or not credentials:
        print(question_selector, credentials)
        return []

    # Если передан только один селектор генерируем faq с помощью ИИ
    if question_selector and not answer_selector:
        print("Создание faq с помощью ИИ")
        return await create_faqs_from_html(file_path, credentials=credentials, selector=question_selector)

    # Если переданы оба селектора парсим html
    if not os.path.exists(file_path):
        return []

    async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
        html_code = await f.read()

    soup = BeautifulSoup(html_code, 'html.parser')
    questions = soup.select(question_selector)
    answers = soup.select(answer_selector)

    if len(questions) != len(answers):
        return []

    return [
        {"question": q.get_text(strip=True), "answer": a.get_text(strip=True)}
        for q, a in zip(questions, answers)
    ]
