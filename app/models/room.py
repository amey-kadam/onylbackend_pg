from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pg_id = Column(Integer, ForeignKey("pgs.id"), nullable=False)
    room_number = Column(String(20), nullable=False)
    floor = Column(Integer, nullable=True, default=1)
    room_type = Column(String(50), nullable=True, default="Standard")
    sharing_type = Column(String(50), nullable=True, default="Sharing")
    daily_stay_charges = Column(Float, nullable=True, default=0.0)
    is_available_for_rent = Column(Boolean, nullable=False, default=True)
    facilities = Column(String(500), nullable=True, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    pg = relationship("PG", back_populates="rooms", lazy="selectin")
    beds = relationship("Bed", back_populates="room", lazy="selectin", cascade="all, delete-orphan")
