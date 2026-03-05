from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.repositories.admin_repository import AdminRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.auth_repository import AuthRepository
from app.security import hash_password, password_meets_policy


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdminRepository(db)
        self.attendance_repo = AttendanceRepository(db)
        self.auth_repo = AuthRepository(db)

    def get_stats(self) -> dict:
        return self.repo.get_system_stats()

    def list_users(
        self,
        *,
        skip: int,
        limit: int,
        search: str | None,
        role: models.UserRole | None,
        is_active: bool | None,
    ) -> list[models.User]:
        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 200))
        return self.repo.list_users(
            skip=safe_skip,
            limit=safe_limit,
            search=search,
            role=role,
            is_active=is_active,
        )

    def update_user_status(self, *, user_id: int, is_active: bool, admin: models.User) -> models.User:
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.id == admin.id:
            raise HTTPException(status_code=400, detail="Cannot change your own active status")
        if admin.role != models.UserRole.super_admin and user.role in {
            models.UserRole.admin,
            models.UserRole.super_admin,
        }:
            raise HTTPException(status_code=403, detail="Only Super Admin can manage Admin/Super Admin accounts")
        user.is_active = is_active
        self.repo.save()
        return user

    def create_user_by_admin(self, *, payload: schemas.AdminCreateUserRequest, actor: models.User) -> models.User:
        role_to_create = payload.role
        if role_to_create in {models.UserRole.admin, models.UserRole.super_admin} and actor.role != models.UserRole.super_admin:
            raise HTTPException(status_code=403, detail="Only Super Admin can create Admin/Super Admin accounts")

        if self.auth_repo.get_user_by_email(payload.email):
            raise HTTPException(status_code=400, detail="Email already registered")

        if not password_meets_policy(payload.password):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Password must contain upper, lower, number, and special character "
                    f"with minimum length {settings.PASSWORD_MIN_LENGTH}"
                ),
            )

        return self.auth_repo.create_user(
            name=payload.name,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            phone=payload.phone,
            state=payload.state,
            city=payload.city,
            role=role_to_create,
        )

    def update_user_role(
        self,
        *,
        user_id: int,
        payload: schemas.UserRoleUpdateRequest,
        actor: models.User,
    ) -> models.User:
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.id == actor.id:
            raise HTTPException(status_code=400, detail="You cannot change your own role")

        target_role = payload.role
        if actor.role != models.UserRole.super_admin:
            raise HTTPException(status_code=403, detail="Only Super Admin can change roles")

        user.role = target_role
        self.repo.save()
        self.auth_repo.revoke_all_user_refresh_tokens(user.id)
        return user

    def list_attendance(
        self,
        *,
        filter_date: date | None,
        date_from: date | None,
        date_to: date | None,
        user_query: str | None,
        skip: int,
        limit: int,
    ) -> tuple[int, list[dict]]:
        if date_from and date_to and date_from > date_to:
            raise HTTPException(status_code=400, detail="date_from cannot be after date_to")
        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 1000))
        total, rows = self.repo.list_attendance(
            filter_date=filter_date,
            date_from=date_from,
            date_to=date_to,
            user_query=user_query,
            skip=safe_skip,
            limit=safe_limit,
        )
        records = [
            {
                "id": attendance.id,
                "user_id": attendance.user_id,
                "user_name": name,
                "user_email": email,
                "date": attendance.date,
                "marked_time": attendance.marked_time,
                "marked_at": attendance.marked_at,
                "ip_address": attendance.ip_address,
                "latitude": attendance.latitude,
                "longitude": attendance.longitude,
                "city": attendance.city,
                "notes": attendance.notes,
            }
            for attendance, name, email in rows
        ]
        return total, records

    def daily_summary(self, *, days: int) -> list[dict]:
        safe_days = max(1, min(days, 365))
        raw_rows = self.repo.daily_summary(safe_days)
        by_date = {row_date: count for row_date, count in raw_rows}

        summary: list[dict] = []
        start_date = date.today() - timedelta(days=safe_days - 1)
        for offset in range(safe_days):
            current = start_date + timedelta(days=offset)
            summary.append({"date": current.isoformat(), "count": by_date.get(current, 0)})
        return summary

    def list_corrections(
        self,
        *,
        status: models.CorrectionStatus | None,
        skip: int,
        limit: int,
    ) -> tuple[int, list[models.AttendanceCorrectionRequest]]:
        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 200))
        return self.attendance_repo.list_corrections(status=status, skip=safe_skip, limit=safe_limit)

    def review_correction(
        self,
        *,
        correction_id: int,
        payload: schemas.AttendanceCorrectionReview,
        admin: models.User,
    ) -> models.AttendanceCorrectionRequest:
        correction = self.attendance_repo.get_correction_by_id(correction_id)
        if not correction:
            raise HTTPException(status_code=404, detail="Correction request not found")
        if correction.status != models.CorrectionStatus.pending:
            raise HTTPException(status_code=400, detail="Correction request is already reviewed")

        correction.status = payload.status
        correction.admin_note = payload.admin_note
        correction.reviewed_by = admin.id
        correction.reviewed_at = datetime.utcnow()

        if payload.status == models.CorrectionStatus.approved:
            attendance = self.attendance_repo.get_user_attendance_by_date(correction.user_id, correction.requested_date)
            if not attendance:
                self.attendance_repo.create_attendance(
                    user_id=correction.user_id,
                    attendance_date=correction.requested_date,
                    ip_address="admin-corrected",
                    notes=f"Attendance correction approved by {admin.email}",
                )
            # create_attendance commits; refresh and return latest correction.
            correction = self.attendance_repo.get_correction_by_id(correction_id)
            if correction is None:
                raise HTTPException(status_code=404, detail="Correction request not found after update")
            return correction

        self.attendance_repo.save()
        return correction

    def list_auth_logs(
        self,
        *,
        skip: int,
        limit: int,
        event_type: models.AuthEventType | None,
    ) -> tuple[int, list[models.AuthAuditLog]]:
        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 200))
        return self.repo.list_auth_logs(skip=safe_skip, limit=safe_limit, event_type=event_type)

    def get_daily_attendance_analytics(self, *, days: int) -> list[dict]:
        safe_days = max(7, min(days, 180))
        start_date = date.today() - timedelta(days=safe_days - 1)
        rows = self.repo.fetch_daily_attendance_counts(from_date=start_date)

        daily_map: dict[date, int] = {}
        for row in rows:
            row_date = self._normalize_date(row.get("attendance_date"))
            if row_date is None:
                continue
            daily_map[row_date] = int(row.get("attendance_count") or 0)

        points: list[dict] = []
        for offset in range(safe_days):
            current = start_date + timedelta(days=offset)
            points.append({"date": current.isoformat(), "count": daily_map.get(current, 0)})
        return points

    def get_monthly_attendance_analytics(self, *, months: int) -> list[dict]:
        safe_months = max(3, min(months, 24))
        today = date.today()
        first_month_start = self._month_start(today.year, today.month, safe_months - 1)

        rows = self.repo.fetch_monthly_attendance_counts(from_date=first_month_start)
        monthly_map = {
            str(row.get("month_key")): {
                "attendance_count": int(row.get("attendance_count") or 0),
                "unique_users": int(row.get("unique_users") or 0),
            }
            for row in rows
        }

        points: list[dict] = []
        for back in range(safe_months - 1, -1, -1):
            year, month = self._subtract_months(today.year, today.month, back)
            month_key = f"{year:04d}-{month:02d}"
            values = monthly_map.get(month_key, {"attendance_count": 0, "unique_users": 0})
            points.append(
                {
                    "month": month_key,
                    "attendance_count": values["attendance_count"],
                    "unique_users": values["unique_users"],
                }
            )
        return points

    def get_user_activity_analytics(self) -> dict:
        return self.repo.fetch_user_activity_counts()

    def get_attendance_trend_analytics(self, *, days: int) -> dict:
        safe_days = max(7, min(days, 90))
        current_end = date.today()
        current_start = current_end - timedelta(days=safe_days - 1)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=safe_days - 1)

        period_counts = self.repo.fetch_period_trend_counts(
            current_start=current_start,
            current_end=current_end,
            previous_start=previous_start,
            previous_end=previous_end,
        )
        current_total = int(period_counts["current_total"])
        previous_total = int(period_counts["previous_total"])

        if previous_total == 0:
            growth_percentage = 100.0 if current_total > 0 else 0.0
        else:
            growth_percentage = ((current_total - previous_total) / previous_total) * 100

        trend = "flat"
        if current_total > previous_total:
            trend = "up"
        elif current_total < previous_total:
            trend = "down"

        return {
            "current_period_total": current_total,
            "previous_period_total": previous_total,
            "growth_percentage": round(growth_percentage, 2),
            "trend": trend,
            "average_per_day": round(current_total / safe_days, 2),
        }

    def get_analytics_overview(self, *, days: int, months: int) -> dict:
        return {
            "daily_attendance": self.get_daily_attendance_analytics(days=days),
            "monthly_attendance": self.get_monthly_attendance_analytics(months=months),
            "user_activity": self.get_user_activity_analytics(),
            "attendance_trend": self.get_attendance_trend_analytics(days=days),
        }

    @staticmethod
    def _normalize_date(raw_value) -> date | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, datetime):
            return raw_value.date()
        if isinstance(raw_value, date):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return datetime.strptime(raw_value, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    @staticmethod
    def _subtract_months(year: int, month: int, months_back: int) -> tuple[int, int]:
        total = (year * 12 + month - 1) - months_back
        target_year = total // 12
        target_month = total % 12 + 1
        return target_year, target_month

    def _month_start(self, year: int, month: int, months_back: int) -> date:
        target_year, target_month = self._subtract_months(year, month, months_back)
        return date(target_year, target_month, 1)
