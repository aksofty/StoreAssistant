import asyncio
import base64
import os
import re
import time
from typing import Any, Dict, List
from loguru import logger
from app import CLIENT_CACHE_DIR
from app.cruds.faq import add_faqs, delete_faqs_by_source, get_faqs, get_faqs_by_ids
from app.cruds.offer import get_offers, get_offers_by_ids, sync_offers
from app.cruds.source_faq import get_faq_sources
from app.cruds.source_yml import get_yml_sources
from app.database import AsyncSessionLocal
from app.schemas.faq import FaqRead
from app.schemas.offer import OfferRead
from app.schemas.source_faq import SourceFaqRead
from app.schemas.source_yml import SourceYmlRead
from app.utils.common import get_rag_cache_path
from app.utils.faq_parser import parse_faq_html
from app.utils.http_downloader import HTTPDownloader
from app.utils.yml_parser import YmlParser
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_gigachat import GigaChatEmbeddings

_XML_ENCODING_RE = re.compile(
    r'(<\?xml\s+version=["\']1\.0["\']\s+encoding=["\'])([^"\']+)(["\'](\s*)\?>)',
    re.IGNORECASE,
)

_OFFER_VECTOR_FIELDS = ["name", "category", "vendor", "vendor_code", "description"]

def fix_xml_encoding(content: str) -> str:
    return _XML_ENCODING_RE.sub(r"\1UTF-8\3", content, count=1)



async def get_embeddings(client_id: str, client_secret: str, scope: str = "GIGACHAT_API_PERS") -> GigaChatEmbeddings:
    """
    Инициализирует объект GigaChatEmbeddings со стратегией по умолчанию (L2-расстояние).
    """
    if not client_id or not client_secret:
        raise ValueError("GIGACHAT_CLIENT_ID и GIGACHAT_CLIENT_SECRET должны быть заполнены.")

    raw_credentials = f"{client_id}:{client_secret}"
    base64_auth = base64.b64encode(raw_credentials.encode("utf-8")).decode("utf-8")
    
    return GigaChatEmbeddings(
        credentials=base64_auth, 
        verify_ssl_certs=False,
        scope=scope
    )


async def faiss_search(query: str, store, max_score: float = 300.0, k: int = 3) -> list[str]:
    # 1. Асинхронный поиск в FAISS
    docs_with_scores = await store.asimilarity_search_with_score(query, k=k)  
    #print(docs_with_scores)
    if not docs_with_scores:
        return []
       
    # 2. Фильтруем ID по score, сохраняя исходный порядок релевантности FAISS
    faq_ids = [doc.metadata['id'] for doc, score in docs_with_scores if score < max_score]
    
    if not faq_ids:
        return []
            
    # 3. Достаем данные из БД
    async with AsyncSessionLocal() as session:
        db_faqs = await get_faqs_by_ids(session, faq_ids)
        
        # Мапим объекты БД в словарь для мгновенного доступа по ID
        faq_map = {
            db_faq.id: FaqRead.model_validate(db_faq).model_dump() 
            for db_faq in db_faqs
        }

    # 4. Собираем финальный список строго в порядке релевантности от FAISS
    faqs = []
    for faq_id in faq_ids:
        if faq := faq_map.get(faq_id):
            faqs.append(f"{faq['question']}: {faq['answer']}")

    return faqs


async def process_single_faq_source(source_db_obj: Any, cache_dir: str, credentials: str, cache_time: int = 2952000) -> Dict[str, Any] | None:
    """Обрабатывает один источник: скачивает, парсит и сохраняет в SQLite напрямую."""
    source = SourceFaqRead.model_validate(source_db_obj).model_dump()
    file_path = get_rag_cache_path(source=source, cache_dir=cache_dir)
    
    try:
        downloader = HTTPDownloader(
            url=source["url"],
            file_path=file_path,
            cache_time=cache_time
        )
        update_source = await downloader.run()
        
        if update_source:

            faq_list = await parse_faq_html(
                file_path=file_path, 
                question_selector=source.get("selector_question"), 
                answer_selector=source.get("selector_answer"),
                credentials=credentials
            )

            if faq_list:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        # Удаляем старое
                        await delete_faqs_by_source(session=session, source_id=source["id"])
                        # Записываем новое
                        await add_faqs(session=session, source_id=source["id"], faq_list=faq_list)
                            
                logger.info(f"Источник {source['id']} обновлен в SQLite. Добавлено {len(faq_list)} вопросов.")
            else:
                logger.warning(f"Файл обновился, но вопросов не найдено. База не очищена.")
                    
        return source
        
    except Exception as e:
        logger.error(f"Ошибка при обработке источника {source.get('url')}: {e}")
        return None

async def init_faq_sources(credentials: str, cache_time: int = 2592000) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        db_sources = await get_faq_sources(session=session)
        
    if not db_sources:
        logger.warning("Faq каталоги не найдены")
        return []

    tasks = [process_single_faq_source(db_source, CLIENT_CACHE_DIR, credentials, cache_time=cache_time) for db_source in db_sources]
    results = await asyncio.gather(*tasks)
    
    faq_sources = [source for source in results if source is not None]

    if faq_sources:
        logger.info("Faq каталоги подготовлены")
    else:
        logger.warning("Ни один Faq каталог не был успешно подготовлен")
        
    return faq_sources



async def init_faqs_store(faiss_dir, embeddings, batch_size = 100, cache_time=2592000):
    async with AsyncSessionLocal() as session:
        db_faqs = await get_faqs(session=session)
        
    docs = [
        Document(
            page_content=faq_dict.get("question", ""),
            metadata={"id": faq_dict["id"]}
        )
        for db_faq in db_faqs
        if (faq_dict := FaqRead.model_validate(db_faq).model_dump())
    ]

    index_path = os.path.join(faiss_dir, "idx_faqs")
    index_exists = os.path.exists(index_path)

    if not index_exists:
        force_update = True
    else:
        file_age = time.time() - os.path.getmtime(index_path)
        force_update = file_age > cache_time


    if force_update:
        if not docs:
            logger.warning("Нет документов для создания индекса FAISS.")
            return None
            
        logger.info(f"Создаем новый индекс idx_faqs для {len(docs)} документов...")
        
        # 1. Создаем базовый индекс по первой порции (батчу)
        first_batch = docs[:batch_size]
        store = await FAISS.afrom_documents(first_batch, embeddings)
        logger.info(f"Обработано документов: {len(first_batch)}/{len(docs)}")
        
        # 2. Добавляем остальные документы батчами по batch_size
        for i in range(batch_size, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            # aadd_documents делает асинхронные запросы к эмбеддингам и добавляет их в FAISS
            await store.aadd_documents(batch)
            logger.info(f"Обработано документов: {min(i + batch_size, len(docs))}/{len(docs)}")
            
            # Небольшая пауза, чтобы гарантированно не спамить API внешних сервисов
            await asyncio.sleep(0.5) 


        
        # 3. Сохраняем готовый индекс на диск
        await asyncio.to_thread(store.save_local, index_path)
        return store

    # Загрузка из кэша, если обновление не требуется
    logger.info("Используем кеш idx_faqs")
    store = await asyncio.to_thread(
        FAISS.load_local, 
        index_path, 
        embeddings, 
        allow_dangerous_deserialization=True
    )
    return store



async def init_offers_store(faiss_dir, embeddings, batch_size=100, force_update=False):
    # 1. Быстро забираем данные из БД и сразу закрываем сессию
    async with AsyncSessionLocal() as session:
        db_offers = await get_offers(session=session)
        
    docs = []

    # 2. Формируем документы (вынесено из блока async with)
    for db_offer in db_offers:
        offer = OfferRead.model_validate(db_offer).model_dump()
        lines = []
        for key in _OFFER_VECTOR_FIELDS:
            value = offer.get(key)
            if value is not None and str(value).strip() != "":
                lines.append(str(value).strip().lower())

        if lines:  # Создаем документ, только если есть текстовое содержимое
            page_content = "; ".join(lines)
            docs.append(
                Document(
                    page_content=page_content, 
                    metadata={"offer_id": offer["offer_id"]}
                )
            )

    index_path = os.path.join(faiss_dir, "idx_offers")
    index_exists = os.path.exists(index_path)

    # 3. Создание или обновление индекса порциями
    if force_update or not index_exists:
        if not docs:
            logger.warning("Нет документов для создания индекса idx_offers.")
            return None
            
        logger.info(f"Создаем новый индекс idx_offers для {len(docs)} офферов...")
        
        # Инициализируем индекс первым батчем (100 документов)
        first_batch = docs[:batch_size]
        store = await FAISS.afrom_documents(first_batch, embeddings)
        logger.info(f"Обработано офферов: {len(first_batch)}/{len(docs)}")
        
        # Добавляем оставшиеся офферы порциями
        for i in range(batch_size, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            await store.aadd_documents(batch)
            logger.info(f"Обработано офферов: {min(i + batch_size, len(docs))}/{len(docs)}")
            
            # Пауза для предотвращения блокировок со стороны API эмбеддингов
            await asyncio.sleep(0.5)
            
        # Асинхронно сохраняем на диск
        await asyncio.to_thread(store.save_local, index_path)
        return store
    

    # 4. Загрузка из кэша
    logger.info("Используем кеш idx_offers")
    store = await asyncio.to_thread(
        FAISS.load_local, 
        index_path, 
        embeddings, 
        allow_dangerous_deserialization=True
    )
    return store
        

def _offer_to_doc(offer: dict) -> Document | None:
    lines = [
        str(offer[key]).strip().lower()
        for key in _OFFER_VECTOR_FIELDS
        if offer.get(key) and str(offer[key]).strip()
    ]
    if not lines:
        return None
    return Document(page_content="; ".join(lines), metadata={"offer_id": offer["offer_id"]})


async def sync_offers_store(
    store: FAISS | None,
    yml_changes: list[dict],
    embeddings,
    faiss_dir: str,
) -> FAISS | None:
    # Собираем все добавленные и удалённые offer_id по всем источникам
    added_ids = {oid for change in yml_changes for oid in change.get("added", [])}
    deleted_ids = {oid for change in yml_changes for oid in change.get("deleted", [])}

    if not added_ids and not deleted_ids:
        logger.info("Изменений в YML не было, FAISS offers не обновляется.")
        return store

    index_path = os.path.join(faiss_dir, "idx_offers")

    # Удаляем из индекса документы удалённых офферов
    if store and deleted_ids:
        # Ищем внутренние docstore ID по metadata["offer_id"]
        ids_to_delete = [
            doc_id
            for doc_id, doc in store.docstore._dict.items()
            if doc.metadata.get("offer_id") in deleted_ids
        ]
        if ids_to_delete:
            store.delete(ids_to_delete)
            logger.info(f"Удалено из FAISS idx_offers: {len(ids_to_delete)} офферов.")

    # Добавляем документы новых офферов
    if added_ids:
        async with AsyncSessionLocal() as session:
            db_offers = await get_offers_by_ids(session, list(added_ids))

        docs = [
            doc for db_offer in db_offers
            if (doc := _offer_to_doc(OfferRead.model_validate(db_offer).model_dump()))
        ]

        if docs:
            if store is None:
                # Индекс ещё не существует — создаём с нуля
                store = await FAISS.afrom_documents(docs, embeddings)
                logger.info(f"Создан новый FAISS idx_offers из {len(docs)} офферов.")
            else:
                await store.aadd_documents(docs)
                logger.info(f"Добавлено в FAISS idx_offers: {len(docs)} офферов.")

    if store:
        await asyncio.to_thread(store.save_local, index_path)

    return store


async def process_single_yml_source(source_db_obj: Any, cache_dir: str, cache_time: int = 3600) -> List[Dict[str, Any]] | None:
    """Скачивает и парсит один YML-источник. Возвращает список офферов или None при ошибке."""
    source = SourceYmlRead.model_validate(source_db_obj).model_dump()
    file_path = get_rag_cache_path(source=source, cache_dir=cache_dir)

    try:
        downloader = HTTPDownloader(
            url=source["url"],
            file_path=file_path,
            cache_time=cache_time,
            processing_func=fix_xml_encoding,
        )

        await downloader.run()

        logger.info(f"Парсим YML: {source['url']}")
        catalog = await YmlParser(file_path).get_catalog_from_yml()

        if not catalog:
            logger.warning(f"Каталог пуст или не удалось распарсить YML для {source['url']}")
            return None

        # Добавляем source_id в каждый оффер (информационное поле)
        for item in catalog:
            item["source_id"] = source["id"]

        logger.info(f"Источник {source['id']}: получено {len(catalog)} офферов.")
        return catalog

    except Exception as e:
        logger.error(f"Ошибка при обработке YML источника {source.get('url')}: {e}")
        return None


async def init_yml_sources(cache_time: int = 3600) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        db_sources = await get_yml_sources(session=session)

    if not db_sources:
        logger.warning("Yml каталоги не найдены")
        return []

    # Параллельно скачиваем и парсим все источники
    tasks = [process_single_yml_source(db_source, CLIENT_CACHE_DIR, cache_time=cache_time) for db_source in db_sources]
    results = await asyncio.gather(*tasks)

    # Сливаем каталоги в один список — первый источник побеждает при совпадении offer_id
    merged: dict[str, dict] = {}
    for catalog in results:
        if catalog is None:
            continue
        for item in catalog:
            oid = str(item.get("offer_id", ""))
            if oid and oid not in merged:
                merged[oid] = item

    if not merged:
        logger.warning("Ни один YML каталог не содержит офферов")
        return []

    merged_catalog = list(merged.values())
    logger.info(f"Объединённый каталог: {len(merged_catalog)} уникальных офферов из {len(db_sources)} источников.")

    async with AsyncSessionLocal() as session:
        changes = await sync_offers(session=session, catalog=merged_catalog)

    logger.info(f"Sync завершён: добавлено {len(changes['added'])}, удалено {len(changes['deleted'])} офферов.")

    # Возвращаем в формате, совместимом с sync_offers_store
    return [{"added": changes["added"], "deleted": changes["deleted"]}]
    