from pydantic import BaseModel, Field
from typing import Optional


class BedCreate(BaseModel):
    room_id: int
    bed_number: str = Field(..., min_length=1, max_length=10)


class BedUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(vacant|occupied)$")
    tenant_id: Optional[int] = None
    price_per_bed: Optional[float] = None


class BedResponse(BaseModel):
    id: int
    room_id: int
    bed_number: str
    status: str
    tenant_name: Optional[str] = None
    room_number: Optional[str] = None
    price_per_bed: Optional[float] = None

    class Config:
        from_attributes = True
