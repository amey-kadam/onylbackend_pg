from pydantic import BaseModel
from typing import List, Optional


class ComplaintSummary(BaseModel):
    id: int
    title: str
    status: str
    tenant_name: Optional[str] = None


class DashboardSummary(BaseModel):
    total_beds: int = 0
    occupied_beds: int = 0
    vacant_beds: int = 0
    total_tenants: int = 0
    active_tenants: int = 0
    rent_collected: float = 0.0
    rent_pending: float = 0.0
    active_complaints: int = 0
    recent_complaints: List[ComplaintSummary] = []
    occupancy_rate: float = 0.0
    current_month: str = ""
