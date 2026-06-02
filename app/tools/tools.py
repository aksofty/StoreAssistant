
import json

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from app.cruds.system_setting import get_int_setting
from app.database import AsyncSessionLocal
from app.cruds.offer import get_offers_by_ids
from app.schemas.offer import OfferRead
from app import CLIENT_TOOL_DIR
from app.tools.loader import load_client_tools

@tool
async def product_search_rag(query: str, config: RunnableConfig, max_price: float|None = None) -> str:
    """
        Поиск товаров в каталоге интернет-магазина.

        ОБЯЗАТЕЛЬНО используй этот инструмент, если пользователь:
        - Ищет конкретный товар.
        - Спрашивает про характеристики, цвет, размер, материал или состав определенного товара.
        - Просит подобрать или порекомендовать товар по параметрам.
        - Интересуется наличием товара или актуальной ценой.

        Аргументы:
        - query: поисковый запрос. Передавай только суть товара, без слов "купить", "найди".
        - max_price: строгое ограничение по максимальной цене, ЕСЛИ пользователь явно назвал бюджет (например, для "до 5000 рублей" передай 5000.0).
    """
    store = config.get("configurable", {}).get("offers_store")
    if not store:
        return "Ошибка: Хранилище товаров временно недоступно."


    max_score = await get_int_setting("faiss.yml.max_score", default=320)
    k = await get_int_setting("faiss.yml.k", default=5)
    fetch_k = await get_int_setting("faiss.yml.fetch_k", default=50)

    price_filter = (lambda meta: meta.get("price", 0) <= max_price) if max_price else None
    docs_with_scores = await store.asimilarity_search_with_score(query, k=k, fetch_k=fetch_k, filter=price_filter)

    offers_ids = [doc.metadata['offer_id'] for doc, score in docs_with_scores if score < max_score]
    if not offers_ids:
        return "Товары по вашему запросу не найдены."

    async with AsyncSessionLocal() as session:
        db_offers = await get_offers_by_ids(session, offers_ids)

    if not db_offers:
        return "Товары по вашему запросу не найдены."

    offers = [OfferRead.model_validate(o).model_dump() for o in db_offers]
    return json.dumps({"type": "offers", "offers": offers})


# Список всех инструментов для привязки к модели
_STATIC_TOOLS = [product_search_rag]
_CLIENT_TOOLS = load_client_tools(CLIENT_TOOL_DIR)

_static_names = {t.name for t in _STATIC_TOOLS}
_unique_client_tools = [t for t in _CLIENT_TOOLS if t.name not in _static_names]

ALL_TOOLS = _STATIC_TOOLS + _unique_client_tools
# Мапа для быстрого вызова по имени
TOOLS_MAP = {t.name: t for t in ALL_TOOLS}