from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NoticeCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=3, max_length=5000)
    priority: Optional[str] = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    pg_id: Optional[int] = None


class NoticeResponse(BaseModel):
    id: int
    pg_id: int
    title: str
    message: str
    priority: Optional[str] = "normal"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NoticeListResponse(BaseModel):
    notices: List[NoticeResponse]
    total: int
