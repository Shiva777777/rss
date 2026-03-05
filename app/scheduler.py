import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def run_daily_attendance_reminders() -> None:
    db = SessionLocal()
    try:
        service = NotificationService(db)
        result = service.send_daily_attendance_reminders()
        logger.info("Daily attendance reminder job completed: %s", result)
    except Exception:
        logger.exception("Daily attendance reminder job failed")
    finally:
        db.close()


def build_scheduler() -> BackgroundScheduler | None:
    if not settings.ENABLE_ATTENDANCE_REMINDER_SCHEDULER:
        return None

    timezone = NotificationService.notification_timezone()
    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.add_job(
        run_daily_attendance_reminders,
        trigger=CronTrigger(
            hour=settings.ATTENDANCE_REMINDER_HOUR,
            minute=settings.ATTENDANCE_REMINDER_MINUTE,
            timezone=timezone,
        ),
        id="daily_attendance_reminders",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    return scheduler
