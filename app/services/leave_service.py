from datetime import date
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.repositories.leave_repository import LeaveRepository
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class LeaveService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = LeaveRepository(db)
        self.notification_service = NotificationService(db)

    def create_request(self, *, user: models.User, payload: schemas.LeaveRequestCreate) -> models.LeaveRequest:
        start_date = payload.start_date
        end_date = payload.end_date
        reason = payload.reason.strip()

        self._validate_leave_dates(start_date=start_date, end_date=end_date)
        if not reason:
            raise HTTPException(status_code=400, detail="Reason cannot be empty")

        if self.repo.has_overlapping_request(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
        ):
            raise HTTPException(
                status_code=409,
                detail="Overlapping leave request already exists (pending/approved)",
            )

        return self.repo.create_request(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        )

    def list_user_requests(
        self,
        *,
        user: models.User,
        status: models.LeaveStatus | None,
        skip: int,
        limit: int,
    ) -> tuple[int, list[models.LeaveRequest]]:
        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 100))
        return self.repo.list_user_requests(
            user_id=user.id,
            status=status,
            skip=safe_skip,
            limit=safe_limit,
        )

    def get_user_request(self, *, user: models.User, leave_id: int) -> models.LeaveRequest:
        leave_request = self.repo.get_user_request_by_id(user.id, leave_id)
        if not leave_request:
            raise HTTPException(status_code=404, detail="Leave request not found")
        return leave_request

    def update_user_request(
        self,
        *,
        user: models.User,
        leave_id: int,
        payload: schemas.LeaveRequestUpdate,
    ) -> models.LeaveRequest:
        leave_request = self.get_user_request(user=user, leave_id=leave_id)
        self._ensure_pending_for_user_action(leave_request)

        next_start = payload.start_date or leave_request.start_date
        next_end = payload.end_date or leave_request.end_date
        self._validate_leave_dates(start_date=next_start, end_date=next_end)

        if self.repo.has_overlapping_request(
            user_id=user.id,
            start_date=next_start,
            end_date=next_end,
            exclude_leave_id=leave_request.id,
        ):
            raise HTTPException(
                status_code=409,
                detail="Overlapping leave request already exists (pending/approved)",
            )

        if payload.reason is not None:
            next_reason = payload.reason.strip()
            if not next_reason:
                raise HTTPException(status_code=400, detail="Reason cannot be empty")
            leave_request.reason = next_reason

        leave_request.start_date = next_start
        leave_request.end_date = next_end
        self.repo.save()
        return leave_request

    def delete_user_request(self, *, user: models.User, leave_id: int) -> None:
        leave_request = self.get_user_request(user=user, leave_id=leave_id)
        self._ensure_pending_for_user_action(leave_request)
        self.repo.delete(leave_request)

    def list_requests_for_admin(
        self,
        *,
        status: models.LeaveStatus | None,
        user_query: str | None,
        skip: int,
        limit: int,
    ) -> tuple[int, list[dict]]:
        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 300))
        total, rows = self.repo.list_requests_for_admin(
            status=status,
            user_query=user_query,
            skip=safe_skip,
            limit=safe_limit,
        )
        records = [
            {
                "id": leave.id,
                "user_id": leave.user_id,
                "start_date": leave.start_date,
                "end_date": leave.end_date,
                "reason": leave.reason,
                "status": leave.status.value,
                "created_at": leave.created_at,
                "user_name": user_name,
                "user_email": user_email,
            }
            for leave, user_name, user_email in rows
        ]
        return total, records

    def review_request(
        self,
        *,
        leave_id: int,
        payload: schemas.LeaveRequestReview,
    ) -> models.LeaveRequest:
        leave_request = self.repo.get_by_id(leave_id)
        if not leave_request:
            raise HTTPException(status_code=404, detail="Leave request not found")

        if leave_request.status != models.LeaveStatus.pending:
            raise HTTPException(status_code=400, detail="Only pending leave requests can be reviewed")

        if payload.status == models.LeaveStatus.pending:
            raise HTTPException(status_code=400, detail="Review status must be approved or rejected")

        leave_request.status = payload.status
        self.repo.save()
        if leave_request.status == models.LeaveStatus.approved:
            try:
                self.notification_service.send_leave_approved(user=leave_request.user, leave_request=leave_request)
            except Exception:
                logger.exception("Leave approval notification failed for leave_id=%s", leave_request.id)
        return leave_request

    @staticmethod
    def _validate_leave_dates(*, start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        if start_date < date.today():
            raise HTTPException(status_code=400, detail="Leave start date cannot be in the past")

    @staticmethod
    def _ensure_pending_for_user_action(leave_request: models.LeaveRequest) -> None:
        if leave_request.status != models.LeaveStatus.pending:
            raise HTTPException(status_code=400, detail="Only pending leave requests can be modified")
