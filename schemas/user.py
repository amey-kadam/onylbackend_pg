from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = None
    password: str = Field(..., min_length=6)
    role: str = Field(default="tenant", pattern="^(owner|tenant)$")


class UserLogin(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    email: Optional[str] = None


class ChangePassword(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
