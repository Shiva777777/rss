from sqlalchemy.orm import Session

from app import models


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> models.User | None:
        return self.db.query(models.User).filter(models.User.id == user_id).first()

    def update_user(self, user: models.User, updates: dict) -> models.User:
        for field, value in updates.items():
            setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return user
