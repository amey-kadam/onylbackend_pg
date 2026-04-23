from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = Field(None, description="Used for password recovery")
    password: str = Field(default="tenant123", min_length=6)
    pg_id: int
    bed_id: Optional[int] = None
    join_date: date
    deposit: float = Field(default=0.0, ge=0)
    monthly_rent: float = Field(default=0.0, ge=0)
    address: Optional[str] = None
    id_proof_url: Optional[str] = None
    aadhar_url: Optional[str] = None
    pan_url: Optional[str] = None
    agreement_url: Optional[str] = None
    ledger_url: Optional[str] = None
    other_documents_url: Optional[str] = None
    locking_period: Optional[int] = 0
    notice_period: Optional[int] = 30
    agreement_period: Optional[int] = 11
    move_out_date: Optional[date] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    bed_id: Optional[int] = None
    deposit: Optional[float] = None
    monthly_rent: Optional[float] = None
    address: Optional[str] = None
    id_proof_url: Optional[str] = None
    aadhar_url: Optional[str] = None
    pan_url: Optional[str] = None
    agreement_url: Optional[str] = None
    ledger_url: Optional[str] = None
    other_documents_url: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|exited)$")
    exit_date: Optional[date] = None
    move_out_date: Optional[date] = None
    locking_period: Optional[int] = None
    notice_period: Optional[int] = None
    agreement_period: Optional[int] = None


class TenantResponse(BaseModel):
    id: int
    user_id: int
    name: str
    phone: str
    email: Optional[str] = None
    pg_id: int
    pg_name: Optional[str] = None
    bed_id: Optional[int] = None
    bed_number: Optional[str] = None
    room_number: Optional[str] = None
    join_date: date
    exit_date: Optional[date] = None
    move_out_date: Optional[date] = None
    locking_period: Optional[int] = 0
    notice_period: Optional[int] = 30
    agreement_period: Optional[int] = 11
    deposit: float
    monthly_rent: float
    address: Optional[str] = None
    id_proof_url: Optional[str] = None
    aadhar_url: Optional[str] = None
    pan_url: Optional[str] = None
    agreement_url: Optional[str] = None
    ledger_url: Optional[str] = None
    other_documents_url: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    tenants: List[TenantResponse]
    total: int
    page: int
    per_page: int


class CheckoutRequest(BaseModel):
    deposit_refund: float = Field(default=0.0, ge=0)
    maintenance_deduction: float = Field(default=0.0, ge=0)
    penalty: float = Field(default=0.0, ge=0)
    checkout_date: Optional[date] = None


class LedgerEntry(BaseModel):
    id: int
    entry_type: str        # "rent" | "maintenance" | "deposit" | "deposit_refund" | "maintenance_deduction" | "penalty"
    title: str
    amount: float
    date: Optional[str] = None
    status: str
    month_year: Optional[str] = None
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    collected_by: Optional[str] = None


class LedgerResponse(BaseModel):
    entries: List[LedgerEntry]
    total_paid: float
    total_pending: float
    total_maintenance_pending: float
    opening_balance: float   # deposit paid
