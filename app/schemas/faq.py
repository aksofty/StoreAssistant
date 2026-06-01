from pydantic import BaseModel, ConfigDict, Field

class FaqRead(BaseModel):
    id: int
    question: str = Field()
    answer: str = Field()
    model_config = ConfigDict(from_attributes=True)
