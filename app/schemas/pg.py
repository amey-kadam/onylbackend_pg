from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PGCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    address: Optional[str] = None


class PGResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    owner_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PGWithStats(PGResponse):
    total_rooms: int = 0
    total_beds: int = 0
    occupied_beds: int = 0
    vacant_beds: int = 0
