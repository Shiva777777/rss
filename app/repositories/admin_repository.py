from datetime import date, timedelta

from sqlalchemy import func, or_
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models


class AdminRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_system_stats(self) -> dict:
        total_users = self.db.query(func.count(models.User.id)).scalar() or 0
        active_users = (
            self.db.query(func.count(models.User.id))
            .filter(models.User.is_active.is_(True))
            .scalar()
            or 0
        )
        total_attendances = self.db.query(func.count(models.Attendance.id)).scalar() or 0
        today_attendances = (
            self.db.query(func.count(models.Attendance.id))
            .filter(models.Attendance.date == date.today())
            .scalar()
            or 0
        )
        pending_corrections = (
            self.db.query(func.count(models.AttendanceCorrectionRequest.id))
            .filter(models.AttendanceCorrectionRequest.status == models.CorrectionStatus.pending)
            .scalar()
            or 0
        )

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_attendances": total_attendances,
            "today_attendances": today_attendances,
            "pending_corrections": pending_corrections,
        }

    def list_users(
        self,
        *,
        skip: int,
        limit: int,
        search: str | None = None,
        role: models.UserRole | None = None,
        is_active: bool | None = None,
    ) -> list[models.User]:
        query = self.db.query(models.User)
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

    def get_user_by_id(self, user_id: int) -> models.User | None:
        return self.db.query(models.User).filter(models.User.id == user_id).first()

    def list_attendance(
        self,
        *,
        filter_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        user_query: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[tuple[models.Attendance, str, str]]]:
        query = (
            self.db.query(models.Attendance, models.User.name, models.User.email)
            .join(models.User, models.Attendance.user_id == models.User.id)
            .order_by(models.Attendance.marked_at.desc())
        )
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

        total = query.count()
        rows = query.offset(skip).limit(limit).all()
        return total, rows

    def daily_summary(self, days: int) -> list[tuple[date, int]]:
        from_date = date.today() - timedelta(days=days - 1)
        rows = (
            self.db.query(
                models.Attendance.date,
                func.count(models.Attendance.id).label("count"),
            )
            .filter(models.Attendance.date >= from_date)
            .group_by(models.Attendance.date)
            .order_by(models.Attendance.date.asc())
            .all()
        )
        return [(r.date, r.count) for r in rows]

    def list_auth_logs(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        event_type: models.AuthEventType | None = None,
    ) -> tuple[int, list[models.AuthAuditLog]]:
        query = self.db.query(models.AuthAuditLog)
        if event_type is not None:
            query = query.filter(models.AuthAuditLog.event_type == event_type)
        query = query.order_by(models.AuthAuditLog.created_at.desc())
        total = query.count()
        rows = query.offset(skip).limit(limit).all()
        return total, rows

    def save(self) -> None:
        self.db.commit()

    def fetch_daily_attendance_counts(self, *, from_date: date) -> list[dict]:
        query = text(
            """
            SELECT
                DATE(a.date) AS attendance_date,
                COUNT(*) AS attendance_count
            FROM attendance a
            WHERE a.date >= :from_date
            GROUP BY DATE(a.date)
            ORDER BY attendance_date ASC
            """
        )
        rows = self.db.execute(query, {"from_date": from_date}).mappings().all()
        return [dict(row) for row in rows]

    def fetch_monthly_attendance_counts(self, *, from_date: date) -> list[dict]:
        query = text(
            """
            SELECT
                DATE_FORMAT(a.date, '%Y-%m') AS month_key,
                COUNT(*) AS attendance_count,
                COUNT(DISTINCT a.user_id) AS unique_users
            FROM attendance a
            WHERE a.date >= :from_date
            GROUP BY DATE_FORMAT(a.date, '%Y-%m')
            ORDER BY month_key ASC
            """
        )
        rows = self.db.execute(query, {"from_date": from_date}).mappings().all()
        return [dict(row) for row in rows]

    def fetch_user_activity_counts(self) -> dict:
        query = text(
            """
            SELECT
                SUM(CASE WHEN u.is_active = 1 THEN 1 ELSE 0 END) AS active_users,
                SUM(CASE WHEN u.is_active = 0 THEN 1 ELSE 0 END) AS inactive_users,
                COUNT(*) AS total_users
            FROM users u
            """
        )
        row = self.db.execute(query).mappings().first()
        if not row:
            return {"active_users": 0, "inactive_users": 0, "total_users": 0}
        return {
            "active_users": int(row["active_users"] or 0),
            "inactive_users": int(row["inactive_users"] or 0),
            "total_users": int(row["total_users"] or 0),
        }

    def fetch_period_trend_counts(
        self,
        *,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date,
    ) -> dict:
        query = text(
            """
            SELECT
                SUM(CASE WHEN a.date BETWEEN :current_start AND :current_end THEN 1 ELSE 0 END) AS current_total,
                SUM(CASE WHEN a.date BETWEEN :previous_start AND :previous_end THEN 1 ELSE 0 END) AS previous_total
            FROM attendance a
            """
        )
        row = self.db.execute(
            query,
            {
                "current_start": current_start,
                "current_end": current_end,
                "previous_start": previous_start,
                "previous_end": previous_end,
            },
        ).mappings().first()
        if not row:
            return {"current_total": 0, "previous_total": 0}
        return {
            "current_total": int(row["current_total"] or 0),
            "previous_total": int(row["previous_total"] or 0),
        }
