from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class PaymentCreate(BaseModel):
    tenant_id: int
    amount: float = Field(..., gt=0)
    status: str = Field(default="paid", pattern="^(paid|partial|unpaid|pending)$")
    payment_date: Optional[date] = None
    month_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    notes: Optional[str] = None
    payment_method: Optional[str] = Field(default="cash", pattern="^(cash|online)$")
    collected_by_user_id: Optional[int] = None
    transaction_id: Optional[str] = None
    screenshot_path: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    tenant_id: int
    tenant_name: Optional[str] = None
    amount: float
    status: str
    payment_date: Optional[date] = None
    month_year: str
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    collected_by: Optional[str] = None
    transaction_id: Optional[str] = None
    screenshot_path: Optional[str] = None
    payment_type: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int
    total_collected: float = 0.0
    total_pending: float = 0.0
    total_refunded: float = 0.0
