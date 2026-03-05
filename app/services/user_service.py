from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.repositories.auth_repository import AuthRepository
from app.repositories.user_repository import UserRepository
from app.security import hash_password, password_meets_policy, verify_password


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.auth_repo = AuthRepository(db)

    def update_profile(self, *, user: models.User, payload: schemas.UserUpdate) -> models.User:
        updates = payload.model_dump(exclude_unset=True)
        return self.user_repo.update_user(user, updates)

    def change_password(self, *, user: models.User, payload: schemas.PasswordChangeRequest) -> None:
        if not verify_password(payload.old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Old password is incorrect")
        if not password_meets_policy(payload.new_password):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Password must contain upper, lower, number, and special character "
                    f"with minimum length {settings.PASSWORD_MIN_LENGTH}"
                ),
            )

        user.hashed_password = hash_password(payload.new_password)
        self.db.commit()
        self.auth_repo.revoke_all_user_refresh_tokens(user.id)
