import asyncio
from typing import List
from bs4 import BeautifulSoup
import aiofiles
from markdownify import markdownify as md
import re

_STRIP_TAGS = ["script", "style", "form", "iframe", "nav", "footer", "header"]


class HTMLCleaner:
    @staticmethod
    async def process(file_path: str, selector: str = None) -> dict:
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            html_content = await f.read()

        def _extract():
            soup = BeautifulSoup(html_content, 'lxml')

            metadata = {}
            canonical_tag = soup.find('link', rel='canonical')
            if canonical_tag:
                metadata["link"] = canonical_tag.get('href')

            target_node = (soup.select_one(selector) if selector else None) or soup.find('body')

            if not target_node:
                return {}

            for tag in target_node(_STRIP_TAGS):
                tag.decompose()

            for a in target_node.find_all('a', href=True):
                a.string = f"{a.get_text(strip=True)}[{a.get('href')}]"

            result = md(str(target_node), heading_style="ATX", bullets="-", strip=["a"])
            result = re.sub(r'\n{3,}', '\n\n', result).strip()

            return {"page_content": split_markdown_text(result), "source": metadata}

        return await asyncio.get_running_loop().run_in_executor(None, _extract)


def split_markdown_text(text: str, chunk_size: int = 4000, overlap: int = 600) -> List[str]:
    if not text or chunk_size <= 0:
        return []

    if len(text) <= chunk_size:
        return [text.strip()]

    separators = ["\n\n", "\n", ". ", " "]
    chunks = []
    current_pos = 0
    text_len = len(text)

    while current_pos < text_len:
        end_pos = min(current_pos + chunk_size, text_len)

        if end_pos == text_len:
            chunk = text[current_pos:].strip()
            if chunk:
                chunks.append(chunk)
            break

        search_zone = text[current_pos:end_pos]
        split_pos = -1

        for sep in separators:
            pos = search_zone.rfind(sep)
            if pos != -1:
                split_pos = current_pos + pos + len(sep)
                break

        if split_pos == -1 or split_pos <= current_pos:
            split_pos = end_pos

        chunk = text[current_pos:split_pos].strip()
        if chunk:
            chunks.append(chunk)

        current_pos = max(split_pos - overlap, current_pos + 1)

    return [re.sub(r'\n{3,}', '\n\n', c) for c in chunks]
