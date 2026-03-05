from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models


class LeaveRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_request(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
        reason: str,
    ) -> models.LeaveRequest:
        leave_request = models.LeaveRequest(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status=models.LeaveStatus.pending,
        )
        self.db.add(leave_request)
        self.db.commit()
        self.db.refresh(leave_request)
        return leave_request

    def get_by_id(self, leave_id: int) -> models.LeaveRequest | None:
        return self.db.query(models.LeaveRequest).filter(models.LeaveRequest.id == leave_id).first()

    def get_user_request_by_id(self, user_id: int, leave_id: int) -> models.LeaveRequest | None:
        return (
            self.db.query(models.LeaveRequest)
            .filter(
                models.LeaveRequest.id == leave_id,
                models.LeaveRequest.user_id == user_id,
            )
            .first()
        )

    def list_user_requests(
        self,
        *,
        user_id: int,
        status: models.LeaveStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[int, list[models.LeaveRequest]]:
        query = self.db.query(models.LeaveRequest).filter(models.LeaveRequest.user_id == user_id)
        if status is not None:
            query = query.filter(models.LeaveRequest.status == status)
        query = query.order_by(models.LeaveRequest.created_at.desc())
        total = query.count()
        records = query.offset(skip).limit(limit).all()
        return total, records

    def list_requests_for_admin(
        self,
        *,
        status: models.LeaveStatus | None = None,
        user_query: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[tuple[models.LeaveRequest, str, str]]]:
        query = (
            self.db.query(models.LeaveRequest, models.User.name, models.User.email)
            .join(models.User, models.LeaveRequest.user_id == models.User.id)
            .order_by(models.LeaveRequest.created_at.desc())
        )
        if status is not None:
            query = query.filter(models.LeaveRequest.status == status)
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

    def has_overlapping_request(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
        exclude_leave_id: int | None = None,
    ) -> bool:
        query = self.db.query(models.LeaveRequest).filter(
            models.LeaveRequest.user_id == user_id,
            models.LeaveRequest.status.in_([models.LeaveStatus.pending, models.LeaveStatus.approved]),
            models.LeaveRequest.start_date <= end_date,
            models.LeaveRequest.end_date >= start_date,
        )
        if exclude_leave_id is not None:
            query = query.filter(models.LeaveRequest.id != exclude_leave_id)
        return query.first() is not None

    def delete(self, leave_request: models.LeaveRequest) -> None:
        self.db.delete(leave_request)
        self.db.commit()

    def save(self) -> None:
        self.db.commit()
