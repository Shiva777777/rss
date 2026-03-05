from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/me", response_model=schemas.NotificationListResponse)
def list_my_notifications(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    service = NotificationService(db)
    total, records = service.list_user_notifications(
        user=current_user,
        skip=skip,
        limit=limit,
    )
    return {"total": total, "records": records}
