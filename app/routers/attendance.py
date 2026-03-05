from typing import Optional

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.services.attendance_service import AttendanceService

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post("/mark", response_model=schemas.AttendanceResponse)
def mark_attendance(
    request: Request,
    payload: schemas.AttendanceMarkRequest = Body(default_factory=schemas.AttendanceMarkRequest),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = AttendanceService(db)
    return service.mark_attendance(
        user=current_user,
        ip_address=_client_ip(request),
        notes=payload.notes,
        latitude=payload.latitude,
        longitude=payload.longitude,
        city=payload.city,
    )


@router.post("/mark-with-location", response_model=schemas.AttendanceResponse)
def mark_attendance_with_location(
    request: Request,
    payload: schemas.AttendanceMarkRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = AttendanceService(db)
    return service.mark_attendance(
        user=current_user,
        ip_address=_client_ip(request),
        notes=payload.notes,
        latitude=payload.latitude,
        longitude=payload.longitude,
        city=payload.city,
    )


@router.get("/today", response_model=Optional[schemas.AttendanceResponse])
def today_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = AttendanceService(db)
    return service.get_today_status(user=current_user)


@router.get("/history", response_model=schemas.AttendanceHistory)
def attendance_history(
    skip: int = 0,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = AttendanceService(db)
    total, records = service.get_history(user=current_user, skip=skip, limit=limit)
    return {"total": total, "records": records}


@router.post("/corrections", response_model=schemas.AttendanceCorrectionResponse)
def create_correction_request(
    payload: schemas.AttendanceCorrectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = AttendanceService(db)
    return service.create_correction_request(user=current_user, payload=payload)


@router.get("/corrections", response_model=schemas.AttendanceCorrectionListResponse)
def list_my_corrections(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = AttendanceService(db)
    total, records = service.list_my_corrections(user=current_user, skip=skip, limit=limit)
    return {"total": total, "records": records}
