import json
import re
from typing import Any, Dict
from urllib.parse import urlparse
from sqlalchemy.types import JSON, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, validates
from app.models.base import Base

class SourceBase:

    @declared_attr
    def id(cls) -> Mapped[int]:
        return mapped_column(primary_key=True)
    
    @declared_attr
    def active(cls) -> Mapped[bool]:
        return mapped_column(default=True)
    

    @declared_attr
    def url(cls) -> Mapped[str]:
        return mapped_column(String(255))
    

    # Валидатор автоматически наследуется всеми дочерними классами
    @validates('url')
    def validate_url(self, key: str, value: str) -> str:
        if not value:
            raise ValueError("URL не может быть пустым")
            
        parsed = urlparse(value)
        if not all([parsed.scheme, parsed.netloc]) or parsed.scheme not in ('http', 'https'):
            raise ValueError(f"Некорректный формат URL: '{value}'. Ожидается http или https")
            
        return value