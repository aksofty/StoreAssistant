from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from loguru import logger

from app import CLIENT_DB_FILE
from app.models.base import Base

engine = create_async_engine(
    f"sqlite+aiosqlite:///{CLIENT_DB_FILE}",
    echo=False,
    connect_args={"timeout": 30},
)


# WAL позволяет читать и писать одновременно без блокировок
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


_DEFAULT_SETTINGS = [
    ("assistant.model", "GigaChat-2-Pro", "АССИСТЕНТ: Модель генерации ответа"),
    ("assistant.scope", "GIGACHAT_API_PERS", "АССИСТЕНТ: Версия API (scope)"),
    (
        "assistant.prompt", 
        """Ты — торговый ассистент интернет-магазина масштабных моделей самолетов. 
Если пользователь ищет конкретный товар, ты обязан в первую очередь использовать инструмент поиска товаров. 
Не пытайся ответить из собственных знаний или **КОНТЕКСТА**, если для этого есть инструмент.
Всегда отвечай ТОЛЬКО на основе предоставленного **КОНТЕКСТА** и данных из инструментов.
Запрещено придумывать услуги, товары, цены, скидки и условия доставки, которых нет в тексте. 
Если ответа нет в **КОНТЕКСТЕ** или инструментах — не угадывай, не используй слова 'возможно' или 'наверное'. 
Вместо этого строго отвечай: 'К сожалению, у меня нет точной информации по этому вопросу. 
Рекомендую обратиться к менеджеру по телефону 8-495-723-9825 или через мессенджер MAX +7-977-380-6043'. 
Пиши коротко, вежливо и строго по делу.""",  
        "АССИСТЕНТ: Системный промпт"
    ),
    ("assistant.temperature", "0.1",  "АССИСТЕНТ: Температура генерации ответа (temperature)"),
    ("assistant.top_p", "0.1",  "АССИСТЕНТ: Вероятность генерации ответа (top_p)"),
    ("assistant.max_tokens", "1024",  "АССИСТЕНТ: Максимальное количество токенов в ответе (max_tokens)"),
    ("assistant.ask_delay", "10",  "АССИСТЕНТ: задержка между вопросами (в секундах)"),
    ("assistant.history_message_count", "4",  "АССИСТЕНТ: максимальное количество сообщений в истории"),
    (
        "assistant.prompt_response_format", 
        """Ты должен строго возвращать валидный JSON. Любой человеческий текст, пояснения или предупреждения пиши ИСКЛЮЧИТЕЛЬНО внутри ключа "text". Никогда не пиши текст за пределами ключей. Используй только стандартные двойные кавычки " (символ ASCII 34). Никаких специальных токенов (<|superquote|> и подобных), обратных кавычек или других символов вместо кавычек. JSON должен быть закрыт — не обрывай ответ на середине.
Если в контексте нет товаров, то не добавляй ключ 'offers' в JSON.
Строгая структура ответа:
{"text": "текст ответа","offers": [{"id": 1, "title": "Название", "price": "100", "description": "описание", "url": "ссылка", "image_url": "ссылка"}]}
""",
        "АССИСТЕНТ: промпт для формирования формата ответа", 
    ),
    ("parser.model", "GigaChat-2", "ПАРСЕР: Модель генерации вопросовна основе контента"),
    (
        "parser.prompt", 
        """Ты — эксперт по подготовке данных для базы знаний. 
        Из предоставленного текста извлеки все смысловые пары вопрос-ответ. 
        Каждый вопрос должен отражать конкретную потребность пользователя, 
        а ответ — исчерпывающе отвечать на него, сохраняя все цифры, условия и детали. 
        Если текст не содержит полезной информации для FAQ — верни пустой список.""",  
        "ПАРСЕР: Промпт для парсинга контента", 
    ),
    ("parser.temperature", "0.1",  "ПАРСЕР: Температура генерации ответа (temperature)"),
    ("parser.top_p", "0.1",  "ПАРСЕР: Вероятность генерации ответа (top_p)"),

    ("faiss.faq.max_score", "300",  "FAISS FAQ: Максимальная релевантность"),
    ("faiss.faq.k", "3",  "FAISS FAQ: Количество результатов"),
    ("faiss.faq.cache_time", "2592000",  "FAISS FAQ: время кэширования в секундах"),

    ("faiss.yml.max_score", "320",  "FAISS YML: Максимальная релевантность"),
    ("faiss.yml.k", "5",  "FAISS YML: Количество результатов"),
    ("faiss.yml.fetch_k", "50",  "FAISS YML: Количество результатов при поиске с фильтром"),
    ("faiss.yml.cache_time", "3600",  "FAISS YML: время кэширования в секундах"),

    ("sync.interval", "3600",  "Интервал синхронизации офферов и FAQ в секундах"),

    ("ask.max_concurrent_requests", "1",  "Максимальное количество одновременных запросов"),
    ("ask.max_queue_size", "5",  "Максимальное количество ожидающих запросов"),
]




async def _seed_defaults():
    params = [
        {"key": key, "value": value, "description": description, "sort": i * 100}
        for i, (key, value, description) in enumerate(reversed(_DEFAULT_SETTINGS))
    ]
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text(
                    "INSERT OR IGNORE INTO system_settings (key, value, description, sort) "
                    "VALUES (:key, :value, :description, :sort)"
                ),
                params,
            )


'''async def _migrate():
    """Одноразовые DDL-миграции для существующих БД."""
    async with engine.begin() as conn:
        for table in ("source_yml", "source_faq"):
            try:
                await conn.execute(text(f"ALTER TABLE {table} DROP COLUMN cache_time"))
                logger.info(f"Миграция: удалена колонка cache_time из {table}")
            except Exception:
                pass  # Колонки уже нет — ок'''


async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        #await _migrate()
        await _seed_defaults()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise
