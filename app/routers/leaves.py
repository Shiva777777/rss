from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.services.leave_service import LeaveService

router = APIRouter()


@router.post("/requests", response_model=schemas.LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    payload: schemas.LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = LeaveService(db)
    return service.create_request(user=current_user, payload=payload)


@router.get("/requests", response_model=schemas.LeaveRequestListResponse)
def list_my_leave_requests(
    status: models.LeaveStatus | None = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = LeaveService(db)
    total, records = service.list_user_requests(
        user=current_user,
        status=status,
        skip=skip,
        limit=limit,
    )
    return {"total": total, "records": records}


@router.get("/requests/{leave_id}", response_model=schemas.LeaveRequestResponse)
def get_my_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = LeaveService(db)
    return service.get_user_request(user=current_user, leave_id=leave_id)


@router.put("/requests/{leave_id}", response_model=schemas.LeaveRequestResponse)
def update_my_leave_request(
    leave_id: int,
    payload: schemas.LeaveRequestUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = LeaveService(db)
    return service.update_user_request(user=current_user, leave_id=leave_id, payload=payload)


@router.delete("/requests/{leave_id}")
def delete_my_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = LeaveService(db)
    service.delete_user_request(user=current_user, leave_id=leave_id)
    return {"message": "Leave request deleted"}
