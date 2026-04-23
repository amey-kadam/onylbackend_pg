import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SqlEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ComplaintStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    pg_id = Column(Integer, ForeignKey("pgs.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(String(2000), nullable=True)
    category = Column(String(50), nullable=True, default="General")
    status = Column(SqlEnum(ComplaintStatus), nullable=False, default=ComplaintStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="complaints", lazy="selectin")
    pg = relationship("PG", back_populates="complaints", lazy="selectin")
