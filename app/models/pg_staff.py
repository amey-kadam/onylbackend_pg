from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PGStaff(Base):
    __tablename__ = "pg_staff"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pg_id = Column(Integer, ForeignKey("pgs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pg = relationship("PG", lazy="selectin")
    user = relationship("User", lazy="selectin")
