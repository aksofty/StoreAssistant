from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict

class OfferBase(BaseModel):
    offer_id: str = Field(..., max_length=255)
    available: bool = True
    name: str = Field(..., max_length=255)
    price: float
    url: str = Field(..., max_length=255)
    category: str | None = Field(None, max_length=255)
    vendor: str | None = Field(None, max_length=255)
    vendor_code: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=255)
    picture: str | None = Field(None, max_length=255)
    params: Dict[str, Any] = Field(default_factory=dict)

class OfferRead(OfferBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class OfferReadMin(BaseModel):
    available: bool = True
    name: str = Field(..., max_length=255)
    price: float
    vendor: str | None = Field(None, max_length=255)
    vendor_code: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=255)
    params: Dict[str, Any] = Field(default_factory=dict)
    url: str = Field(..., max_length=255)
    picture: str | None = Field(None, max_length=255)
    
    model_config = ConfigDict(from_attributes=True)