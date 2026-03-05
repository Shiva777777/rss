from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app import models


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[models.User]:
        return self.db.query(models.User).filter(models.User.email == email).first()

    def create_user(
        self,
        *,
        name: str,
        email: str,
        hashed_password: str,
        phone: str | None = None,
        state: str | None = None,
        city: str | None = None,
        role: models.UserRole = models.UserRole.user,
    ) -> models.User:
        user = models.User(
            name=name,
            email=email,
            phone=phone,
            state=state,
            city=city,
            hashed_password=hashed_password,
            role=role,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def invalidate_reset_tokens(self, user_id: int) -> None:
        self.db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.user_id == user_id,
            models.PasswordResetToken.is_used.is_(False),
        ).update({"is_used": True})
        self.db.commit()

    def create_reset_token(self, *, user_id: int, token_hash: str, expires_at: datetime) -> models.PasswordResetToken:
        token = models.PasswordResetToken(
            user_id=user_id,
            token=token_hash,
            expires_at=expires_at,
            is_used=False,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_active_reset_token(self, token_hash: str) -> Optional[models.PasswordResetToken]:
        return (
            self.db.query(models.PasswordResetToken)
            .filter(
                models.PasswordResetToken.token == token_hash,
                models.PasswordResetToken.is_used.is_(False),
            )
            .first()
        )

    def mark_reset_token_used(self, reset_token: models.PasswordResetToken) -> None:
        reset_token.is_used = True
        self.db.commit()

    def create_refresh_token(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None,
        user_agent: str | None,
    ) -> models.RefreshToken:
        token = models.RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_refresh_token(self, token_hash: str) -> Optional[models.RefreshToken]:
        return self.db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()

    def revoke_refresh_token(self, token: models.RefreshToken) -> None:
        token.revoked_at = datetime.utcnow()
        self.db.commit()

    def revoke_all_user_refresh_tokens(self, user_id: int) -> None:
        self.db.query(models.RefreshToken).filter(
            models.RefreshToken.user_id == user_id,
            models.RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": datetime.utcnow()})
        self.db.commit()

    def create_auth_audit_log(
        self,
        *,
        event_type: models.AuthEventType,
        email: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        detail: str | None = None,
    ) -> models.AuthAuditLog:
        audit = models.AuthAuditLog(
            user_id=user_id,
            email=email,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else None,
            detail=detail,
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit
