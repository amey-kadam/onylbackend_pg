import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SqlEnum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BedStatus(str, enum.Enum):
    VACANT = "vacant"
    OCCUPIED = "occupied"


class Bed(Base):
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    bed_number = Column(String(10), nullable=False)
    status = Column(SqlEnum(BedStatus), nullable=False, default=BedStatus.VACANT)
    price_per_bed = Column(Float, nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    room = relationship("Room", back_populates="beds", lazy="selectin")
    tenant = relationship("Tenant", back_populates="bed", uselist=False, lazy="selectin")
