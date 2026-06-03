import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from app import CLIENT_FAISS_DIR
from app.assistants.store_assistant import StoreAssistant
from app.config import Config
from app.database import init_db
from app.cruds.system_setting import get_int_setting, get_str_setting
from app.state import sync_event
from app.cruds.bot_user_message import delete_old_messages
from app.database import AsyncSessionLocal
from app.utils.faiss import get_embeddings, init_faq_sources, init_faqs_store, init_offers_store, init_yml_sources, sync_offers_store


async def _sync_loop(
        assistant: StoreAssistant,
        embeddings,
        credentials: str,
        faiss_dir: str,
):
    while True:
        interval = await get_int_setting("sync.interval", default=3600)
        yml_cache_time = await get_int_setting("faiss.yml.cache_time", default=3600)
        faq_cache_time = await get_int_setting("faiss.faq.cache_time", default=2592000)
        history_max_age = await get_int_setting("history.delete_interval", default=604800)
        
        try:
            await asyncio.wait_for(sync_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass

        sync_event.clear()
        try:
            yml_changes = await init_yml_sources(cache_time=yml_cache_time)
            updated_offer_store = await sync_offers_store(assistant.offers_store, yml_changes, embeddings, faiss_dir)
            assistant.offers_store = updated_offer_store
            logger.info("Плановая синхронизация офферов завершена.")

            _, updated_faq_ids = await init_faq_sources(credentials=credentials, cache_time=faq_cache_time)
            updated_faqs_store = await init_faqs_store(faiss_dir, embeddings, cache_time=faq_cache_time, updated_ids=updated_faq_ids)
            assistant.faqs_store = updated_faqs_store
            logger.info("Плановая синхронизация faq завершена.")

            async with AsyncSessionLocal() as session:
                deleted = await delete_old_messages(session, max_age_seconds=history_max_age)
            logger.info(f"Очистка истории сообщений: удалено {deleted} записей.")

        except Exception as e:
            logger.error(f"Ошибка при плановой синхронизации: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):

    #Инициализация баз данных
    await init_db()
    #Инициализация векторных баз
    embeddings = await get_embeddings(client_id=Config.GIGACHAT_CLIENT_ID, client_secret=Config.GIGACHAT_CLIENT_SECRET)
    
    #Инициализация yml источников
    await init_yml_sources() 
    offers_store = await init_offers_store(CLIENT_FAISS_DIR, embeddings, force_update=False)

    #Инициализация faq источников
    _, updated_faq_ids = await init_faq_sources(credentials=Config.GIGACHAT_CREDENTIALS)
    faqs_store = await init_faqs_store(CLIENT_FAISS_DIR, embeddings, updated_ids=updated_faq_ids)
  
    

    max_concurrent = await get_int_setting("ask.max_concurrent_requests", default=1)
    max_queue = await get_int_setting("ask.max_queue_size", default=5)
    app.state.gigachat_semaphore = asyncio.Semaphore(max_concurrent)
    app.state.max_queue_size = max_queue

    prompt = await get_str_setting("assistant.prompt", default="")
    response_prompt = await get_str_setting("assistant.prompt_response_format", default="")
    system_prompt = f"{prompt}\n{response_prompt}"


    assistant = StoreAssistant(
        offers_store = offers_store,
        faqs_store = faqs_store,
        system_prompt=system_prompt,
        max_connections=max_concurrent
    )

    app.state.assistant = assistant

    sync_task = asyncio.create_task(
        _sync_loop(
            assistant=assistant,
            embeddings=embeddings,
            credentials=Config.GIGACHAT_CREDENTIALS,
            faiss_dir=CLIENT_FAISS_DIR
        )
    )

    yield  # Здесь приложение работает
    # Код после yield выполняется ПРИ ВЫКЛЮЧЕНИИ
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    print("Остановка приложения...")