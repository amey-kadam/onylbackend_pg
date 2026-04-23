from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PG(Base):
    __tablename__ = "pgs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    address = Column(String(500), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="owned_pgs", lazy="selectin")
    rooms = relationship("Room", back_populates="pg", lazy="selectin", cascade="all, delete-orphan")
    tenants = relationship("Tenant", back_populates="pg", lazy="selectin")
    complaints = relationship("Complaint", back_populates="pg", lazy="selectin")
    notices = relationship("Notice", back_populates="pg", lazy="selectin", cascade="all, delete-orphan")
