from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app import models


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


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(default=None, min_length=20)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: models.UserRole


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    state: Optional[str]
    city: Optional[str]
    role: models.UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    state: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


class AdminCreateUserRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    state: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=8)
    role: models.UserRole = models.UserRole.user


class UserRoleUpdateRequest(BaseModel):
    role: models.UserRole


class AttendanceMarkRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    city: Optional[str] = Field(default=None, max_length=100)


class AttendanceResponse(BaseModel):
    id: int
    user_id: int
    date: date
    marked_time: Optional[time] = None
    marked_at: datetime
    ip_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceHistory(BaseModel):
    total: int
    records: list[AttendanceResponse]


class LeaveRequestCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=5, max_length=1200)


class LeaveRequestUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = Field(default=None, min_length=5, max_length=1200)


class LeaveRequestReview(BaseModel):
    status: models.LeaveStatus


class LeaveRequestResponse(BaseModel):
    id: int
    user_id: int
    start_date: date
    end_date: date
    reason: str
    status: models.LeaveStatus
    created_at: datetime
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class LeaveRequestListResponse(BaseModel):
    total: int
    records: list[LeaveRequestResponse]


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    message: str
    status: models.NotificationStatus
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    total: int
    records: list[NotificationResponse]


class AdminAnnouncementCreate(BaseModel):
    message: str = Field(..., min_length=5, max_length=2000)
    email_subject: Optional[str] = Field(default=None, max_length=200)


class AnnouncementDispatchResponse(BaseModel):
    total_users: int
    sent: int
    failed: int
    skipped: int


class AttendanceCorrectionCreate(BaseModel):
    requested_date: date
    reason: str = Field(..., min_length=10, max_length=1200)


class AttendanceCorrectionReview(BaseModel):
    status: models.CorrectionStatus
    admin_note: Optional[str] = Field(default=None, max_length=1200)


class AttendanceCorrectionResponse(BaseModel):
    id: int
    user_id: int
    requested_date: date
    reason: str
    status: str
    admin_note: Optional[str]
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceCorrectionListResponse(BaseModel):
    total: int
    records: list[AttendanceCorrectionResponse]


class AdminStats(BaseModel):
    total_users: int
    total_attendances: int
    today_attendances: int
    active_users: int
    pending_corrections: int


class DailyAttendance(BaseModel):
    date: date
    count: int


class AttendanceListResponse(BaseModel):
    total: int
    records: list[dict]


class AuthAuditResponse(BaseModel):
    id: int
    user_id: Optional[int]
    email: Optional[str]
    event_type: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    detail: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuthAuditListResponse(BaseModel):
    total: int
    records: list[AuthAuditResponse]


class DailyAttendancePoint(BaseModel):
    date: str
    count: int


class MonthlyAttendancePoint(BaseModel):
    month: str
    attendance_count: int
    unique_users: int


class UserActivityAnalytics(BaseModel):
    active_users: int
    inactive_users: int
    total_users: int


class AttendanceTrendAnalytics(BaseModel):
    current_period_total: int
    previous_period_total: int
    growth_percentage: float
    trend: str
    average_per_day: float


class AnalyticsOverviewResponse(BaseModel):
    daily_attendance: list[DailyAttendancePoint]
    monthly_attendance: list[MonthlyAttendancePoint]
    user_activity: UserActivityAnalytics
    attendance_trend: AttendanceTrendAnalytics
