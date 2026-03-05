from datetime import date

from sqlalchemy import exists, func
from sqlalchemy.orm import Session

from app import models


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        *,
        user_id: int,
        message: str,
        status: models.NotificationStatus = models.NotificationStatus.pending,
    ) -> models.Notification:
        notification = models.Notification(
            user_id=user_id,
            message=message,
            status=status,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def update_status(
        self,
        notification: models.Notification,
        status: models.NotificationStatus,
    ) -> models.Notification:
        notification.status = status
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def list_user_notifications(
        self,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[models.Notification]]:
        query = (
            self.db.query(models.Notification)
            .filter(models.Notification.user_id == user_id)
            .order_by(models.Notification.created_at.desc())
        )
        total = query.count()
        records = query.offset(skip).limit(limit).all()
        return total, records

    def list_active_users(self) -> list[models.User]:
        return (
            self.db.query(models.User)
            .filter(models.User.is_active.is_(True))
            .order_by(models.User.id.asc())
            .all()
        )

    def list_active_users_missing_attendance(self, attendance_date: date) -> list[models.User]:
        attendance_exists = exists().where(
            models.Attendance.user_id == models.User.id,
            models.Attendance.date == attendance_date,
        )
        return (
            self.db.query(models.User)
            .filter(
                models.User.is_active.is_(True),
                ~attendance_exists,
            )
            .order_by(models.User.id.asc())
            .all()
        )

    def has_notification_message_for_date(
        self,
        *,
        user_id: int,
        message: str,
        notification_date: date,
    ) -> bool:
        return (
            self.db.query(models.Notification.id)
            .filter(
                models.Notification.user_id == user_id,
                models.Notification.message == message,
                func.date(models.Notification.created_at) == notification_date,
            )
            .first()
            is not None
        )
