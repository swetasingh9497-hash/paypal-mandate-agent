from typing import Literal, Optional
from pydantic import BaseModel, Field

class Mandate(BaseModel):
    item: str
    max_total: float = Field(gt=0)
    currency: str = "USD"
    min_rating: Optional[float] = Field(default=None, ge=0, le=5)
    max_delivery_days: Optional[int] = Field(default=None, gt=0)
    blocked_merchants: list[str] = []
    auto_approve_under: float = 0.0   # is amount ke neeche bina poochhe pay

class Product(BaseModel):
    id: str
    title: str
    price: float
    currency: str
    rating: Optional[float] = None
    merchant: str
    delivery_days: Optional[int] = None
    url: str

class Decision(BaseModel):
    action: Literal["auto_pay", "needs_approval", "reject"]
    reasons: list[str]