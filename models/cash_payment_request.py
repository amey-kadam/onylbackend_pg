import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum as SqlEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CashRequestStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CashPaymentRequest(Base):
    __tablename__ = "cash_payment_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    receiver_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # owner/staff who receives cash
    amount = Column(Float, nullable=False)
    month_year = Column(String(7), nullable=False)   # "2026-04"
    otp = Column(String(6), nullable=False)
    status = Column(SqlEnum(CashRequestStatus), nullable=False, default=CashRequestStatus.PENDING)
    notes = Column(String(300), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant = relationship("Tenant", lazy="selectin")
    receiver = relationship("User", foreign_keys=[receiver_user_id], lazy="selectin")
