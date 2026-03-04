from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ────────────────────────────────────────────────────────────────────────────
# Auth Schemas
# ────────────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    state: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# ────────────────────────────────────────────────────────────────────────────
# User Schemas
# ────────────────────────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    state: Optional[str]
    city: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    state: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)


# ────────────────────────────────────────────────────────────────────────────
# Attendance Schemas
# ────────────────────────────────────────────────────────────────────────────
class AttendanceResponse(BaseModel):
    id: int
    user_id: int
    date: date
    marked_at: datetime

    class Config:
        from_attributes = True


class AttendanceHistory(BaseModel):
    total: int
    records: List[AttendanceResponse]


# ────────────────────────────────────────────────────────────────────────────
# Admin Schemas
# ────────────────────────────────────────────────────────────────────────────
class AdminStats(BaseModel):
    total_users: int
    total_attendances: int
    today_attendances: int
    active_users: int


class DailyAttendance(BaseModel):
    date: date
    count: int
