from datetime import date
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.repositories.attendance_repository import AttendanceRepository
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class AttendanceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AttendanceRepository(db)
        self.notification_service = NotificationService(db)

    def mark_attendance(
        self,
        *,
        user: models.User,
        ip_address: str | None,
        notes: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        city: str | None = None,
    ) -> models.Attendance:
        today = date.today()
        existing = self.repo.get_user_attendance_by_date(user.id, today)
        if existing:
            raise HTTPException(status_code=409, detail="Attendance already marked for today")

        if (latitude is None) != (longitude is None):
            raise HTTPException(status_code=400, detail="Latitude and longitude must be provided together")

        normalized_city = city.strip() if city and city.strip() else None
        if latitude is not None and normalized_city is None:
            normalized_city = "Unknown"

        attendance = self.repo.create_attendance(
            user_id=user.id,
            attendance_date=today,
            ip_address=ip_address,
            latitude=latitude,
            longitude=longitude,
            city=normalized_city,
            notes=notes,
        )
        try:
            self.notification_service.send_attendance_confirmation(user=user, attendance=attendance)
        except Exception:
            logger.exception("Attendance notification failed for user_id=%s", user.id)
        return attendance

    def get_today_status(self, *, user: models.User) -> models.Attendance | None:
        return self.repo.get_user_attendance_by_date(user.id, date.today())

    def get_history(self, *, user: models.User, skip: int, limit: int) -> tuple[int, list[models.Attendance]]:
        safe_limit = max(1, min(limit, settings.MAX_ATTENDANCE_HISTORY_LIMIT))
        safe_skip = max(0, skip)
        return self.repo.get_history(user.id, safe_skip, safe_limit)

    def create_correction_request(
        self, *, user: models.User, payload: schemas.AttendanceCorrectionCreate
    ) -> models.AttendanceCorrectionRequest:
        requested_date = payload.requested_date
        if requested_date > date.today():
            raise HTTPException(status_code=400, detail="Requested date cannot be in the future")

        attendance = self.repo.get_user_attendance_by_date(user.id, requested_date)
        if attendance:
            raise HTTPException(status_code=400, detail="Attendance already exists for requested date")

        pending = self.repo.get_pending_correction(user.id, requested_date)
        if pending:
            raise HTTPException(status_code=400, detail="Pending correction request already exists for this date")

        return self.repo.create_correction_request(
            user_id=user.id,
            requested_date=requested_date,
            reason=payload.reason.strip(),
        )

    def list_my_corrections(
        self,
        *,
        user: models.User,
        skip: int,
        limit: int,
    ) -> tuple[int, list[models.AttendanceCorrectionRequest]]:
        safe_limit = max(1, min(limit, 100))
        safe_skip = max(0, skip)
        return self.repo.list_user_corrections(user.id, safe_skip, safe_limit)
