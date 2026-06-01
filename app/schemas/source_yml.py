from pydantic import ConfigDict
from app.schemas.source_base import SourceBase

class SourceYmlRead(SourceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)