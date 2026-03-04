from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/mark", response_model=schemas.AttendanceResponse)
def mark_attendance(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark attendance for the current day. Only once per day allowed."""
    today = date.today()
    existing = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.user_id == current_user.id,
            models.Attendance.date == today,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Attendance already marked for today",
        )

    client_ip = request.client.host if request.client else "unknown"
    attendance = models.Attendance(
        user_id=current_user.id,
        date=today,
        ip_address=client_ip,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


@router.get("/today", response_model=Optional[schemas.AttendanceResponse])
def today_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Check if the user has already marked attendance today."""
    today = date.today()
    record = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.user_id == current_user.id,
            models.Attendance.date == today,
        )
        .first()
    )
    return record


@router.get("/history", response_model=schemas.AttendanceHistory)
def attendance_history(
    skip: int = 0,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get attendance history for the current user."""
    query = (
        db.query(models.Attendance)
        .filter(models.Attendance.user_id == current_user.id)
        .order_by(models.Attendance.date.desc())
    )
    total = query.count()
    records = query.offset(skip).limit(limit).all()
    return {"total": total, "records": records}
