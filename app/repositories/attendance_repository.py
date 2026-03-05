from datetime import date

from sqlalchemy.orm import Session

from app import models


class AttendanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_attendance_by_date(self, user_id: int, attendance_date: date) -> models.Attendance | None:
        return (
            self.db.query(models.Attendance)
            .filter(
                models.Attendance.user_id == user_id,
                models.Attendance.date == attendance_date,
            )
            .first()
        )

    def create_attendance(
        self,
        *,
        user_id: int,
        attendance_date: date,
        ip_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        city: str | None = None,
        notes: str | None = None,
    ) -> models.Attendance:
        attendance = models.Attendance(
            user_id=user_id,
            date=attendance_date,
            ip_address=ip_address,
            latitude=latitude,
            longitude=longitude,
            city=city,
            notes=notes,
        )
        self.db.add(attendance)
        self.db.commit()
        self.db.refresh(attendance)
        return attendance

    def get_history(self, user_id: int, skip: int, limit: int) -> tuple[int, list[models.Attendance]]:
        query = (
            self.db.query(models.Attendance)
            .filter(models.Attendance.user_id == user_id)
            .order_by(models.Attendance.date.desc())
        )
        total = query.count()
        records = query.offset(skip).limit(limit).all()
        return total, records

    def get_pending_correction(self, user_id: int, requested_date: date) -> models.AttendanceCorrectionRequest | None:
        return (
            self.db.query(models.AttendanceCorrectionRequest)
            .filter(
                models.AttendanceCorrectionRequest.user_id == user_id,
                models.AttendanceCorrectionRequest.requested_date == requested_date,
                models.AttendanceCorrectionRequest.status == models.CorrectionStatus.pending,
            )
            .first()
        )

    def create_correction_request(
        self,
        *,
        user_id: int,
        requested_date: date,
        reason: str,
    ) -> models.AttendanceCorrectionRequest:
        request = models.AttendanceCorrectionRequest(
            user_id=user_id,
            requested_date=requested_date,
            reason=reason,
            status=models.CorrectionStatus.pending,
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def list_user_corrections(self, user_id: int, skip: int, limit: int) -> tuple[int, list[models.AttendanceCorrectionRequest]]:
        query = (
            self.db.query(models.AttendanceCorrectionRequest)
            .filter(models.AttendanceCorrectionRequest.user_id == user_id)
            .order_by(models.AttendanceCorrectionRequest.created_at.desc())
        )
        total = query.count()
        records = query.offset(skip).limit(limit).all()
        return total, records

    def list_corrections(
        self,
        *,
        status: models.CorrectionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[models.AttendanceCorrectionRequest]]:
        query = self.db.query(models.AttendanceCorrectionRequest)
        if status is not None:
            query = query.filter(models.AttendanceCorrectionRequest.status == status)
        query = query.order_by(models.AttendanceCorrectionRequest.created_at.desc())
        total = query.count()
        rows = query.offset(skip).limit(limit).all()
        return total, rows

    def get_correction_by_id(self, correction_id: int) -> models.AttendanceCorrectionRequest | None:
        return (
            self.db.query(models.AttendanceCorrectionRequest)
            .filter(models.AttendanceCorrectionRequest.id == correction_id)
            .first()
        )

    def save(self) -> None:
        self.db.commit()
