import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.repositories.notification_repository import NotificationRepository
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = NotificationRepository(db)
        self.email_service = EmailService()

    def list_user_notifications(
        self,
        *,
        user: models.User,
        skip: int,
        limit: int,
    ) -> tuple[int, list[models.Notification]]:
        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 100))
        return self.repo.list_user_notifications(user_id=user.id, skip=safe_skip, limit=safe_limit)

    def send_attendance_confirmation(
        self,
        *,
        user: models.User,
        attendance: models.Attendance,
    ) -> models.Notification:
        attendance_time = attendance.marked_time.isoformat() if attendance.marked_time else "N/A"
        message = f"Attendance confirmed for {attendance.date.isoformat()} at {attendance_time}."
        body = (
            f"Hello {user.name},\n\n"
            f"Your attendance has been recorded successfully.\n"
            f"Date: {attendance.date.isoformat()}\n"
            f"Time: {attendance_time}\n"
            f"City: {attendance.city or 'N/A'}\n\n"
            "Regards,\n"
            "RSS Attendance System"
        )
        return self._deliver_notification(
            user=user,
            message=message,
            subject="Attendance Confirmation - RSS Attendance System",
            body=body,
        )

    def send_leave_approved(
        self,
        *,
        user: models.User,
        leave_request: models.LeaveRequest,
    ) -> models.Notification:
        message = (
            "Your leave request "
            f"({leave_request.start_date.isoformat()} to {leave_request.end_date.isoformat()}) has been approved."
        )
        body = (
            f"Hello {user.name},\n\n"
            f"Your leave request has been approved.\n"
            f"Start Date: {leave_request.start_date.isoformat()}\n"
            f"End Date: {leave_request.end_date.isoformat()}\n"
            f"Reason: {leave_request.reason}\n\n"
            "Regards,\n"
            "RSS Attendance System"
        )
        return self._deliver_notification(
            user=user,
            message=message,
            subject="Leave Request Approved - RSS Attendance System",
            body=body,
        )

    def broadcast_announcement(
        self,
        *,
        actor: models.User,
        message: str,
        email_subject: str | None = None,
    ) -> dict:
        clean_message = message.strip()
        if not clean_message:
            raise HTTPException(status_code=400, detail="Announcement message cannot be empty")
        subject = email_subject.strip() if email_subject and email_subject.strip() else "Admin Announcement - RSS Attendance System"
        users = self.repo.list_active_users()

        counters = {"total_users": len(users), "sent": 0, "failed": 0, "skipped": 0}
        for user in users:
            body = (
                f"Hello {user.name},\n\n"
                f"Announcement from {actor.name}:\n\n"
                f"{clean_message}\n\n"
                "Regards,\n"
                "RSS Attendance System"
            )
            notification = self._deliver_notification(
                user=user,
                message=clean_message,
                subject=subject,
                body=body,
            )
            self._increment_counters(counters, notification.status)
        return counters

    def send_daily_attendance_reminders(
        self,
        *,
        reminder_date: date | None = None,
    ) -> dict:
        current_date = reminder_date or self.current_local_date()
        message = f"Attendance reminder for {current_date.isoformat()}: please mark your attendance today."
        users = self.repo.list_active_users_missing_attendance(current_date)

        counters = {"total_users": len(users), "sent": 0, "failed": 0, "skipped": 0}
        for user in users:
            if self.repo.has_notification_message_for_date(
                user_id=user.id,
                message=message,
                notification_date=current_date,
            ):
                counters["skipped"] += 1
                continue

            body = (
                f"Hello {user.name},\n\n"
                "This is your daily attendance reminder.\n"
                f"Please mark your attendance for {current_date.isoformat()}.\n\n"
                "Regards,\n"
                "RSS Attendance System"
            )
            notification = self._deliver_notification(
                user=user,
                message=message,
                subject="Daily Attendance Reminder - RSS Attendance System",
                body=body,
            )
            self._increment_counters(counters, notification.status)
        return counters

    def _deliver_notification(
        self,
        *,
        user: models.User,
        message: str,
        subject: str,
        body: str,
    ) -> models.Notification:
        notification = self.repo.create_notification(
            user_id=user.id,
            message=message,
            status=models.NotificationStatus.pending,
        )

        if not self.email_service.is_configured():
            return self.repo.update_status(notification, models.NotificationStatus.skipped)

        sent, error = self.email_service.send_email(
            to_email=user.email,
            subject=subject,
            body=body,
        )
        target_status = models.NotificationStatus.sent if sent else models.NotificationStatus.failed
        updated = self.repo.update_status(notification, target_status)
        if not sent and error:
            logger.warning("Notification email failed for user_id=%s: %s", user.id, error)
        return updated

    @staticmethod
    def current_local_date() -> date:
        timezone = NotificationService.notification_timezone()
        return datetime.now(timezone).date()

    @staticmethod
    def _increment_counters(counter: dict, status: models.NotificationStatus) -> None:
        if status == models.NotificationStatus.sent:
            counter["sent"] += 1
        elif status == models.NotificationStatus.failed:
            counter["failed"] += 1
        else:
            counter["skipped"] += 1

    @staticmethod
    def notification_timezone() -> ZoneInfo:
        try:
            return ZoneInfo(settings.ATTENDANCE_REMINDER_TIMEZONE)
        except Exception:
            logger.warning(
                "Invalid ATTENDANCE_REMINDER_TIMEZONE=%s, falling back to UTC",
                settings.ATTENDANCE_REMINDER_TIMEZONE,
            )
            return ZoneInfo("UTC")
