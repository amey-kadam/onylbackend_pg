import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Enum as SqlEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    EXITED = "exited"


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    pg_id = Column(Integer, ForeignKey("pgs.id"), nullable=False)
    bed_id = Column(Integer, ForeignKey("beds.id"), nullable=True, unique=True)
    join_date = Column(Date, nullable=False)
    exit_date = Column(Date, nullable=True)
    move_out_date = Column(Date, nullable=True)
    locking_period = Column(Integer, nullable=True, default=0)   # months
    notice_period = Column(Integer, nullable=True, default=30)   # days
    agreement_period = Column(Integer, nullable=True, default=11) # months
    deposit = Column(Float, nullable=False, default=0.0)
    monthly_rent = Column(Float, nullable=False, default=0.0)
    id_proof_url = Column(String(500), nullable=True)
    address = Column(String(500), nullable=True)
    aadhar_url = Column(String(500), nullable=True)
    pan_url = Column(String(500), nullable=True)
    agreement_url = Column(String(500), nullable=True)
    ledger_url = Column(String(500), nullable=True)
    other_documents_url = Column(String(1000), nullable=True)
    status = Column(SqlEnum(TenantStatus), nullable=False, default=TenantStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="tenant_profile", lazy="selectin")
    pg = relationship("PG", back_populates="tenants", lazy="selectin")
    bed = relationship("Bed", back_populates="tenant", lazy="selectin")
    payments = relationship("Payment", back_populates="tenant", lazy="selectin", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="tenant", lazy="selectin", cascade="all, delete-orphan")
