from datetime import date
import csv
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_admin

router = APIRouter()


def _apply_attendance_filters(
    query,
    filter_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user_query: Optional[str] = None,
):
    if filter_date:
        query = query.filter(models.Attendance.date == filter_date)
    else:
        if date_from:
            query = query.filter(models.Attendance.date >= date_from)
        if date_to:
            query = query.filter(models.Attendance.date <= date_to)

    if user_query:
        pattern = f"%{user_query.strip()}%"
        query = query.filter(
            or_(
                models.User.name.ilike(pattern),
                models.User.email.ilike(pattern),
            )
        )

    return query


@router.get("/stats", response_model=schemas.AdminStats)
def get_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_admin),
):
    """Get overall system statistics."""
    total_users = db.query(func.count(models.User.id)).scalar()
    active_users = (
        db.query(func.count(models.User.id))
        .filter(models.User.is_active.is_(True))
        .scalar()
    )
    total_atts = db.query(func.count(models.Attendance.id)).scalar()
    today_atts = (
        db.query(func.count(models.Attendance.id))
        .filter(models.Attendance.date == date.today())
        .scalar()
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_attendances": total_atts,
        "today_attendances": today_atts,
    }


@router.get("/users", response_model=List[schemas.UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = Query(None, description="Search by name/email/phone/state/city"),
    role: Optional[models.UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active/inactive"),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_admin),
):
    """List users with optional filters (admin only)."""
    query = db.query(models.User)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.User.name.ilike(pattern),
                models.User.email.ilike(pattern),
                models.User.phone.ilike(pattern),
                models.User.state.ilike(pattern),
                models.User.city.ilike(pattern),
            )
        )

    if role is not None:
        query = query.filter(models.User.role == role)

    if is_active is not None:
        query = query.filter(models.User.is_active.is_(is_active))

    return query.order_by(models.User.created_at.desc()).offset(skip).limit(limit).all()


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool = Query(..., description="Set true to activate, false to deactivate"),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    """Activate or deactivate a user account."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own active status")

    user.is_active = is_active
    db.commit()
    db.refresh(user)

    action = "activated" if is_active else "deactivated"
    return {"message": f"User {user.email} {action}"}


@router.delete("/users/{user_id}")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    """Backward-compatible endpoint to deactivate a user account."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    db.commit()
    return {"message": f"User {user.email} deactivated"}


@router.get("/attendance")
def list_attendance(
    filter_date: Optional[date] = Query(None, description="Filter by specific date (YYYY-MM-DD)"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    user_query: Optional[str] = Query(None, description="Search by user name/email"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_admin),
):
    """List attendance records with optional date/user filters."""
    query = (
        db.query(models.Attendance, models.User.name, models.User.email)
        .join(models.User, models.Attendance.user_id == models.User.id)
        .order_by(models.Attendance.marked_at.desc())
    )
    query = _apply_attendance_filters(
        query=query,
        filter_date=filter_date,
        date_from=date_from,
        date_to=date_to,
        user_query=user_query,
    )

    total = query.count()
    results = query.offset(skip).limit(limit).all()

    records = [
        {
            "id": att.id,
            "user_id": att.user_id,
            "user_name": name,
            "user_email": email,
            "date": att.date,
            "marked_at": att.marked_at,
            "ip_address": att.ip_address,
        }
        for att, name, email in results
    ]
    return {"total": total, "records": records}


@router.get("/attendance/export")
def export_attendance_csv(
    filter_date: Optional[date] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    user_query: Optional[str] = Query(None),
    max_rows: int = Query(5000, ge=1, le=20000),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_admin),
):
    """Export attendance records as CSV."""
    query = (
        db.query(models.Attendance, models.User.name, models.User.email)
        .join(models.User, models.Attendance.user_id == models.User.id)
        .order_by(models.Attendance.marked_at.desc())
    )
    query = _apply_attendance_filters(
        query=query,
        filter_date=filter_date,
        date_from=date_from,
        date_to=date_to,
        user_query=user_query,
    )

    rows = query.limit(max_rows).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["attendance_id", "user_id", "user_name", "user_email", "date", "marked_at", "ip_address"])
    for att, name, email in rows:
        writer.writerow(
            [
                att.id,
                att.user_id,
                name,
                email,
                att.date.isoformat() if att.date else "",
                att.marked_at.isoformat() if att.marked_at else "",
                att.ip_address or "",
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
    _: models.User = Depends(get_current_admin),
):
    """Get daily attendance count for the past N days."""
    rows = (
        db.query(
            models.Attendance.date,
            func.count(models.Attendance.id).label("count"),
        )
        .group_by(models.Attendance.date)
        .order_by(models.Attendance.date.desc())
        .limit(days)
        .all()
    )
    return [{"date": str(r.date), "count": r.count} for r in rows]
