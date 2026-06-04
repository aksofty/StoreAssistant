import os
import json
import re
from urllib.parse import urlparse, unquote

def get_rag_cache_path(source: dict, cache_dir: str):
    file_name = format_url_to_filename(source["url"])
    file_path = os.path.join(cache_dir, f"{file_name}.cache")
    return file_path

def format_url_to_filename(url):
    parsed = urlparse(url)
    
    # 1. Обрабатываем домен: убираем точки
    domain = parsed.netloc.replace('.', '_')
    
    # 2. Получаем имя: берем последнюю часть пути, если путь пустой - берем предпоследнюю
    path_parts = [p for p in unquote(parsed.path).split('/') if p]
    
    if not path_parts:
        name = "index"
    else:
        # Берем последний элемент и отрезаем расширение (например, .html)
        name = os.path.splitext(path_parts[-1])[0]
    
    return f"{domain}_{name}"

_SPECIAL_TOKEN_RE = re.compile(r'<\|[^|>]+\|>')

def _clean_raw(s: str) -> str:
    """Убирает служебные токены модели и заменяет их кавычками."""
    # <|superquote|> и подобные токены — замена на "
    str = s.replace('<|superquote|>', '"').replace('""', '"')
    return _SPECIAL_TOKEN_RE.sub('"', str)


def _extract_offers_from_text(text_val: str) -> tuple[str, list | None]:
    """Extracts offers embedded inside a text value when LLM puts them in the wrong field."""
    m = re.search(r',\s*"offers"\s*:\s*(\[[\s\S]*\])\s*\}?\s*$', text_val)
    if not m:
        return text_val, None
    clean_text = text_val[:m.start()].strip()
    try:
        offers = json.loads(m.group(1))
        if isinstance(offers, list):
            return clean_text, offers
    except (json.JSONDecodeError, ValueError):
        pass
    return text_val, None


def normalize_answer(raw: str) -> str:
    """Приводит ответ ассистента к валидной JSON-строке вида {"text": "...", "offers": [...]}."""
    if not raw or not isinstance(raw, str):
        return json.dumps({"text": str(raw or "")}, ensure_ascii=False)

    raw = _clean_raw(raw)


    # 1. Стандартный парсинг (до 2 уровней вложенности)
    for candidate in (raw, raw.strip().strip('"')):
        try:
            data = json.loads(candidate)
            # Ассистент может вернуть JSON-строку внутри JSON-строки
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, ValueError):
                    pass
            if isinstance(data, dict) and "text" in data:
                text_val = str(data["text"])
                offers = data.get("offers") or None
                if not offers:
                    text_val, offers = _extract_offers_from_text(text_val)
                result: dict = {"text": text_val}
                if offers:
                    result["offers"] = offers
                return json.dumps(result, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. Убираем двойное экранирование кавычек и пробуем снова
    try:
        data = json.loads(raw.replace('\\"', '"'))
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, ValueError):
                pass
        if isinstance(data, dict) and "text" in data:
            text_val = str(data["text"])
            offers = data.get("offers") or None
            if not offers:
                text_val, offers = _extract_offers_from_text(text_val)
            result = {"text": text_val}
            if offers:
                result["offers"] = offers
            return json.dumps(result, ensure_ascii=False)
    except (json.JSONDecodeError, ValueError):
        pass

    # 3. Regex-экстракция text и offers (до step 2.5, чтобы не потерять offers при unclosed JSON)
    result = {}

    text_match = re.search(r'\\?"text\\?"\s*:\s*\\?"([\s\S]*?)(?:\\?",\s*\\?"offers|\\?"?\s*})', raw)
    if text_match:
        text_val = text_match.group(1)
        text_val = text_val.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")
        result["text"] = text_val

    # \\?" — опциональный \ перед закрывающей " (ЛЛМ иногда экранирует структурные кавычки)
    # (?:\\n|\s)* — матчит как реальный пробел, так и literal \n в незакрытом JSON
    offers_match = re.search(r'"offers\\?"\s*:\s*(\[[\s\S]*?\])(?:\\n|\s)*[},]', raw)
    if offers_match:
        offers_str = offers_match.group(1)
        # Fallback: раскрываем escape-последовательности (ЛЛМ мог экранировать все кавычки и \n)
        unescaped = offers_str.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
        for offers_candidate in (offers_str, unescaped):
            try:
                result["offers"] = json.loads(offers_candidate)
                break
            except (json.JSONDecodeError, ValueError):
                pass

    if result:
        return json.dumps(result, ensure_ascii=False)

    # 2.5. Ремонт незакрытого JSON (LLM иногда не добавляет закрывающую скобку)
    stripped = raw.rstrip()
    for suffix in ('"}', '}', '"]}', '"}]}'):
        try:
            data = json.loads(stripped + suffix)
            if isinstance(data, dict) and "text" in data:
                result = {"text": str(data["text"])}
                if data.get("offers"):
                    result["offers"] = data["offers"]
                return json.dumps(result, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            pass

    # 3.5. Жадная экстракция: берём всё после "text": " до конца строки
    # Спасает когда внутри строки есть незакрытая кавычка и нет закрывающей }
    m = re.search(r'"text"\s*:\s*"([\s\S]+)', raw)
    if m:
        text_val = m.group(1)
        # Срезаем хвостовой мусор: кавычки, скобки, пробелы
        text_val = re.sub(r'["\s,}\]]+$', '', text_val)
        text_val = text_val.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")
        return json.dumps({"text": text_val}, ensure_ascii=False)

    # 4. Просто оборачиваем строку как text
    return json.dumps({"text": raw}, ensure_ascii=False)