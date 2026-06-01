import os
import time
import httpx
from charset_normalizer import from_bytes
from loguru import logger
from typing import Callable, Optional


class HTTPDownloader:

    def __init__(
        self,
        url: str,
        file_path: str,
        cache_time: int = 3600,
        processing_func: Optional[Callable[[str], str]] = None,
    ):
        self.url = url
        self.file_path = file_path
        self.cache_time = cache_time
        self.processing_func = processing_func

    async def run(self) -> bool:
        if not self._should_update():
            logger.info(f"Используем кэш источника {self.url}")
            return False
        logger.info(f"Обновляем кэш источника {self.url}")
        return await self.download_and_save()

    def _should_update(self) -> bool:
        if not os.path.exists(self.file_path):
            return True
        if self.cache_time == 0:
            return False
        file_age = time.time() - os.path.getmtime(self.file_path)
        return file_age > self.cache_time

    async def download_and_save(self) -> bool:
        content = await self._download()
        if content is None:
            return False
        if self.processing_func:
            content = self.processing_func(content)
        if not content:
            return False
        await self._write_cache(content)
        return True

    async def _download(self) -> Optional[str]:
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=20.0, headers=headers
            ) as client:
                response = await client.get(self.url)
                response.raise_for_status()
                raw_bytes = response.content
                result = from_bytes(raw_bytes).best()
                return str(result) if result else response.text
        except Exception as e:
            logger.warning(f"Ошибка при скачивании {self.url}: {e}")
            return None

    async def _write_cache(self, content: str) -> None:
        try:
            dir_name = os.path.dirname(self.file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
        except Exception as e:
            logger.warning(f"Ошибка записи кэша {self.file_path}: {e}")
