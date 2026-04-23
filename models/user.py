import enum
from sqlalchemy import Column, Integer, String, Enum as SqlEnum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"
    TENANT = "tenant"
    STAFF = "staff"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    role = Column(SqlEnum(UserRole), nullable=False, default=UserRole.TENANT)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owned_pgs = relationship("PG", back_populates="owner", lazy="selectin")
    tenant_profile = relationship("Tenant", back_populates="user", uselist=False, lazy="selectin")
    subscription = relationship("ClientSubscription", back_populates="user", uselist=False, lazy="selectin")
