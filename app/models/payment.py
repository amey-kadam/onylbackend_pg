import enum
from sqlalchemy import Column, Integer, Float, String, ForeignKey, Date, DateTime, Enum as SqlEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PaymentStatus(str, enum.Enum):
    PAID = "paid"
    PARTIAL = "partial"
    UNPAID = "unpaid"
    PENDING = "pending"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(SqlEnum(PaymentStatus), nullable=False, default=PaymentStatus.UNPAID)
    payment_date = Column(Date, nullable=True)
    month_year = Column(String(7), nullable=False)  # e.g. "2026-03"
    notes = Column(String(500), nullable=True)
    payment_method = Column(String(20), nullable=True, default="cash")  # "cash" | "online"
    collected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    transaction_id = Column(String(100), nullable=True)
    screenshot_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="payments", lazy="selectin")
