from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class BedInfo(BaseModel):
    id: int
    bed_number: str
    status: str
    tenant_name: Optional[str] = None
    price_per_bed: Optional[float] = None
    in_notice_period: Optional[bool] = False
    move_out_date: Optional[date] = None

    class Config:
        from_attributes = True


class RoomCreate(BaseModel):
    pg_id: int
    room_number: str = Field(..., min_length=1, max_length=20)
    floor: Optional[int] = 1
    room_type: Optional[str] = "Standard"
    sharing_type: Optional[str] = "Sharing"
    daily_stay_charges: Optional[float] = 0.0
    is_available_for_rent: Optional[bool] = True
    facilities: Optional[str] = ""
    num_beds: Optional[int] = Field(default=1, ge=1, le=10, description="Auto-create this many beds")


class RoomUpdate(BaseModel):
    room_number: Optional[str] = Field(None, min_length=1, max_length=20)
    floor: Optional[int] = None
    room_type: Optional[str] = None
    sharing_type: Optional[str] = None
    daily_stay_charges: Optional[float] = None
    is_available_for_rent: Optional[bool] = None
    facilities: Optional[str] = None


class RoomResponse(BaseModel):
    id: int
    pg_id: int
    room_number: str
    floor: Optional[int] = None
    room_type: Optional[str] = None
    sharing_type: Optional[str] = None
    daily_stay_charges: Optional[float] = None
    is_available_for_rent: Optional[bool] = True
    facilities: Optional[str] = None
    created_at: Optional[datetime] = None
    beds: List[BedInfo] = []

    class Config:
        from_attributes = True
