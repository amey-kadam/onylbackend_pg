from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pg_id = Column(Integer, ForeignKey("pgs.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(String(5000), nullable=False)
    priority = Column(String(20), nullable=True, default="normal")  # low, normal, high, urgent
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    pg = relationship("PG", back_populates="notices", lazy="selectin")
