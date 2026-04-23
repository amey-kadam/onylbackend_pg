from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CashPaymentInitiate(BaseModel):
    amount: float = Field(..., gt=0)
    month_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    receiver_user_id: int
    notes: Optional[str] = None


class CashPaymentVerify(BaseModel):
    request_id: int
    otp: str = Field(..., min_length=6, max_length=6)


class CashPaymentRequestResponse(BaseModel):
    id: int
    tenant_id: int
    tenant_name: Optional[str] = None
    receiver_user_id: int
    receiver_name: Optional[str] = None
    amount: float
    month_year: str
    otp: Optional[str] = None   # Only shown to owner/staff
    status: str
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StaffListResponse(BaseModel):
    id: int
    name: str
    phone: str
    role: str
