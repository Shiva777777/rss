from datetime import date
import csv
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import require_roles
from app.services.admin_service import AdminService
from app.services.leave_service import LeaveService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/stats", response_model=schemas.AdminStats)
def get_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles(models.UserRole.super_admin, models.UserRole.admin)),
):
    service = AdminService(db)
    return service.get_stats()


@router.get("/users", response_model=list[schemas.UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = Query(None, description="Search by name/email/phone/state/city"),
    role: Optional[models.UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active/inactive"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles(models.UserRole.super_admin, models.UserRole.admin)),
):
    service = AdminService(db)
    return service.list_users(
        skip=skip,
        limit=limit,
        search=search,
        role=role,
        is_active=is_active,
    )


@router.post("/users", response_model=schemas.UserResponse)
def create_user(
    payload: schemas.AdminCreateUserRequest,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_roles(models.UserRole.super_admin, models.UserRole.admin)),
):
    service = AdminService(db)
    return service.create_user_by_admin(payload=payload, actor=actor)


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool = Query(..., description="Set true to activate, false to deactivate"),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_roles(models.UserRole.super_admin, models.UserRole.admin)),
):
    service = AdminService(db)
    user = service.update_user_status(user_id=user_id, is_active=is_active, admin=admin)
    action = "activated" if is_active else "deactivated"
    return {"message": f"User {user.email} {action}"}


@router.patch("/users/{user_id}/role", response_model=schemas.UserResponse)
def update_user_role(
    user_id: int,
    payload: schemas.UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_roles(models.UserRole.super_admin)),
):
    service = AdminService(db)
    return service.update_user_role(user_id=user_id, payload=payload, actor=actor)


@router.delete("/users/{user_id}")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_roles(models.UserRole.super_admin, models.UserRole.admin)),
):
    service = AdminService(db)
    user = service.update_user_status(user_id=user_id, is_active=False, admin=admin)
    return {"message": f"User {user.email} deactivated"}


@router.get("/attendance", response_model=schemas.AttendanceListResponse)
def list_attendance(
    filter_date: Optional[date] = Query(None, description="Filter by specific date (YYYY-MM-DD)"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    user_query: Optional[str] = Query(None, description="Search by user name/email"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    total, records = service.list_attendance(
        filter_date=filter_date,
        date_from=date_from,
        date_to=date_to,
        user_query=user_query,
        skip=skip,
        limit=limit,
    )
    return {"total": total, "records": records}


@router.get("/attendance/export")
def export_attendance_csv(
    filter_date: Optional[date] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    user_query: Optional[str] = Query(None),
    max_rows: int = Query(5000, ge=1, le=20000),
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    total, records = service.list_attendance(
        filter_date=filter_date,
        date_from=date_from,
        date_to=date_to,
        user_query=user_query,
        skip=0,
        limit=max_rows,
    )

    if total == 0:
        raise HTTPException(status_code=404, detail="No attendance records found for export")

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "attendance_id",
            "user_id",
            "user_name",
            "user_email",
            "date",
            "time",
            "marked_at",
            "ip_address",
            "latitude",
            "longitude",
            "city",
            "notes",
        ]
    )
    for record in records:
        writer.writerow(
            [
                record["id"],
                record["user_id"],
                record["user_name"],
                record["user_email"],
                record["date"].isoformat() if record["date"] else "",
                record["marked_time"].isoformat() if record["marked_time"] else "",
                record["marked_at"].isoformat() if record["marked_at"] else "",
                record["ip_address"] or "",
                record["latitude"] if record["latitude"] is not None else "",
                record["longitude"] if record["longitude"] is not None else "",
                record["city"] or "",
                record["notes"] or "",
            ]
        )

    filename = f"attendance_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/attendance/daily-summary")
def daily_attendance_summary(
    days: int = Query(30, ge=1, le=365, description="Number of past days to summarize"),
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    return service.daily_summary(days=days)


@router.get("/analytics/daily", response_model=list[schemas.DailyAttendancePoint])
def analytics_daily_attendance(
    days: int = Query(30, ge=7, le=180),
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    return service.get_daily_attendance_analytics(days=days)


@router.get("/analytics/monthly", response_model=list[schemas.MonthlyAttendancePoint])
def analytics_monthly_attendance(
    months: int = Query(12, ge=3, le=24),
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    return service.get_monthly_attendance_analytics(months=months)


@router.get("/analytics/user-activity", response_model=schemas.UserActivityAnalytics)
def analytics_user_activity(
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    return service.get_user_activity_analytics()


@router.get("/analytics/trends", response_model=schemas.AttendanceTrendAnalytics)
def analytics_attendance_trend(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    return service.get_attendance_trend_analytics(days=days)


@router.get("/analytics/overview", response_model=schemas.AnalyticsOverviewResponse)
def analytics_overview(
    days: int = Query(30, ge=7, le=180),
    months: int = Query(12, ge=3, le=24),
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    return service.get_analytics_overview(days=days, months=months)


@router.get("/attendance/corrections", response_model=schemas.AttendanceCorrectionListResponse)
def list_attendance_corrections(
    status: models.CorrectionStatus | None = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    total, records = service.list_corrections(status=status, skip=skip, limit=limit)
    return {"total": total, "records": records}


@router.patch("/attendance/corrections/{correction_id}/review", response_model=schemas.AttendanceCorrectionResponse)
def review_attendance_correction(
    correction_id: int,
    payload: schemas.AttendanceCorrectionReview,
    db: Session = Depends(get_db),
    admin: models.User = Depends(
        require_roles(models.UserRole.super_admin, models.UserRole.admin, models.UserRole.moderator)
    ),
):
    service = AdminService(db)
    return service.review_correction(correction_id=correction_id, payload=payload, admin=admin)


@router.get("/leaves/requests", response_model=schemas.LeaveRequestListResponse)
def list_leave_requests(
    status: models.LeaveStatus | None = Query(None),
    user_query: str | None = Query(None, description="Search by user name/email"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles(models.UserRole.super_admin, models.UserRole.admin)),
):
    service = LeaveService(db)
    total, records = service.list_requests_for_admin(
        status=status,
        user_query=user_query,
        skip=skip,
        limit=limit,
    )
    return {"total": total, "records": records}


@router.patch("/leaves/requests/{leave_id}/review", response_model=schemas.LeaveRequestResponse)
def review_leave_request(
    leave_id: int,
    payload: schemas.LeaveRequestReview,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles(models.UserRole.super_admin, models.UserRole.admin)),
):
    service = LeaveService(db)
    return service.review_request(leave_id=leave_id, payload=payload)


@router.get("/leaves/history", response_model=schemas.LeaveRequestListResponse)
def leave_history(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles(models.UserRole.super_admin, models.UserRole.admin)),
):
    service = LeaveService(db)
    total, records = service.list_requests_for_admin(
        status=None,
        user_query=None,
        skip=skip,
        limit=limit,
    )
    return {"total": total, "records": records}


@router.post("/announcements", response_model=schemas.AnnouncementDispatchResponse)
def create_announcement(
    payload: schemas.AdminAnnouncementCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_roles(models.UserRole.super_admin, models.UserRole.admin)),
):
    service = NotificationService(db)
    return service.broadcast_announcement(
        actor=actor,
        message=payload.message,
        email_subject=payload.email_subject,
    )


@router.get("/auth-audit", response_model=schemas.AuthAuditListResponse)
def list_auth_audit_logs(
    skip: int = 0,
    limit: int = 100,
    event_type: models.AuthEventType | None = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles(models.UserRole.super_admin)),
):
    service = AdminService(db)
    total, records = service.list_auth_logs(skip=skip, limit=limit, event_type=event_type)
    return {"total": total, "records": records}
