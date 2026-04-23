from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = "General"
    pg_id: Optional[int] = None


class ComplaintUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|in_progress|resolved)$")


class ComplaintResponse(BaseModel):
    id: int
    tenant_id: int
    tenant_name: Optional[str] = None
    pg_id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ComplaintListResponse(BaseModel):
    complaints: List[ComplaintResponse]
    total: int
    pending: int = 0
    in_progress: int = 0
    resolved: int = 0
