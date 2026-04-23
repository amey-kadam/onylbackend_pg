from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ClientSubscription(Base):
    __tablename__ = "client_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan = Column(String(20), default="basic", nullable=False)  # basic, standard, premium, custom
    status = Column(String(20), default="active", nullable=False)  # active, expired, suspended, trial
    expiry_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ── Feature flags ─────────────────────────────────────────────────────
    feature_rent_management = Column(Boolean, default=True, nullable=False)
    feature_complaint_management = Column(Boolean, default=True, nullable=False)
    feature_visitor_entry = Column(Boolean, default=False, nullable=False)
    feature_staff_management = Column(Boolean, default=False, nullable=False)
    feature_expense_tracking = Column(Boolean, default=False, nullable=False)
    feature_analytics = Column(Boolean, default=False, nullable=False)
    feature_email_alerts = Column(Boolean, default=False, nullable=False)
    feature_whatsapp_alerts = Column(Boolean, default=False, nullable=False)
    feature_notice_board = Column(Boolean, default=True, nullable=False)
    feature_maintenance_tracking = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="subscription")
