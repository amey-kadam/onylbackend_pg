import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Enum as SqlEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MaintenanceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    WAIVED = "waived"


class MaintenanceBill(Base):
    __tablename__ = "maintenance_bills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pg_id = Column(Integer, ForeignKey("pgs.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)  # None = all tenants
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(SqlEnum(MaintenanceStatus), nullable=False, default=MaintenanceStatus.PENDING)
    month_year = Column(String(7), nullable=True)  # "2026-04"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    pg = relationship("PG", lazy="selectin")
    tenant = relationship("Tenant", lazy="selectin")
