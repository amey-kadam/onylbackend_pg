from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class MaintenanceBillCreate(BaseModel):
    pg_id: int
    tenant_id: Optional[int] = None
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    amount: float = Field(..., gt=0)
    due_date: Optional[date] = None
    month_year: Optional[str] = None


class MaintenanceBillUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(pending|paid|waived)$")


class MaintenanceBillResponse(BaseModel):
    id: int
    pg_id: int
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    amount: float
    due_date: Optional[date] = None
    status: str
    month_year: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MaintenanceBillListResponse(BaseModel):
    bills: List[MaintenanceBillResponse]
    total: int
    total_pending: float
    total_paid: float
