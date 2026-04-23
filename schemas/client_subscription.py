from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class FeatureFlags(BaseModel):
    rent_management: bool = True
    complaint_management: bool = True
    visitor_entry: bool = False
    staff_management: bool = False
    expense_tracking: bool = False
    analytics: bool = False
    email_alerts: bool = False
    whatsapp_alerts: bool = False
    notice_board: bool = True
    maintenance_tracking: bool = True


class ClientSubscriptionCreate(BaseModel):
    user_id: int
    plan: str = "basic"
    status: str = "active"
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    features: FeatureFlags = FeatureFlags()


class ClientSubscriptionUpdate(BaseModel):
    plan: Optional[str] = None
    status: Optional[str] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    features: Optional[FeatureFlags] = None


class ClientInfo(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: str
    pg_name: Optional[str] = None
    pg_count: int = 0


class ClientSubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan: str
    status: str
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    features: FeatureFlags
    created_at: datetime
    updated_at: datetime
    client: ClientInfo

    class Config:
        from_attributes = True


class SaasStatsResponse(BaseModel):
    total_clients: int
    active_clients: int
    expired_clients: int
    suspended_clients: int
    trial_clients: int
    basic_plan: int
    standard_plan: int
    premium_plan: int
    custom_plan: int
    total_features_enabled: int
