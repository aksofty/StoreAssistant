from typing import Optional

from pydantic import ConfigDict, Field

from app.schemas.source_base import SourceBase


class SourceFaqRead(SourceBase):
    id: int
    selector_question: Optional[str] = Field(None, max_length=255)
    selector_answer: Optional[str] = Field(None, max_length=255)

    model_config = ConfigDict(from_attributes=True)