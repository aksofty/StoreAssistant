from pydantic import BaseModel, Field

class SourceBase(BaseModel):
    active: bool = True
    url: str = Field(..., max_length=255)