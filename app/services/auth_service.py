from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.repositories.auth_repository import AuthRepository
from app.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    password_meets_policy,
    verify_password,
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AuthRepository(db)

    def register(self, payload: schemas.UserRegister) -> models.User:
        existing = self.repo.get_user_by_email(payload.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        if not password_meets_policy(payload.password):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Password must contain upper, lower, number, and special character "
                    f"with minimum length {settings.PASSWORD_MIN_LENGTH}"
                ),
            )

        return self.repo.create_user(
            name=payload.name,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            phone=payload.phone,
            state=payload.state,
            city=payload.city,
            role=models.UserRole.user,
        )

    def login(self, *, email: str, password: str, ip_address: str | None, user_agent: str | None) -> schemas.Token:
        user = self.repo.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            self.repo.create_auth_audit_log(
                event_type=models.AuthEventType.login_failed,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Invalid credentials",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            self.repo.create_auth_audit_log(
                event_type=models.AuthEventType.login_failed,
                email=email,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Inactive account",
            )
            raise HTTPException(status_code=403, detail="Account is disabled")

        token_payload = self._issue_token_pair(user, ip_address, user_agent)
        self.repo.create_auth_audit_log(
            event_type=models.AuthEventType.login_success,
            email=user.email,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return token_payload

    def refresh(self, *, refresh_token: str, ip_address: str | None, user_agent: str | None) -> schemas.Token:
        token_hash = hash_token(refresh_token)
        stored_token = self.repo.get_refresh_token(token_hash)

        if not stored_token or stored_token.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        if stored_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Refresh token expired")

        user = self.db.query(models.User).filter(models.User.id == stored_token.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User account is not active")

        self.repo.revoke_refresh_token(stored_token)
        token_payload = self._issue_token_pair(user, ip_address, user_agent)
        self.repo.create_auth_audit_log(
            event_type=models.AuthEventType.token_refreshed,
            email=user.email,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return token_payload

    def logout(
        self,
        *,
        user: models.User,
        refresh_token: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        if refresh_token:
            token_hash = hash_token(refresh_token)
            stored_token = self.repo.get_refresh_token(token_hash)
            if stored_token and stored_token.user_id == user.id and stored_token.revoked_at is None:
                self.repo.revoke_refresh_token(stored_token)
        else:
            self.repo.revoke_all_user_refresh_tokens(user.id)

        self.repo.create_auth_audit_log(
            event_type=models.AuthEventType.logout,
            email=user.email,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def forgot_password(self, payload: schemas.ForgotPasswordRequest) -> dict:
        user = self.repo.get_user_by_email(payload.email)
        if not user:
            return {"message": "If the email exists, a reset link has been sent."}

        self.repo.invalidate_reset_tokens(user.id)
        raw_token = generate_secure_token()
        self.repo.create_reset_token(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES),
        )
        self.repo.create_auth_audit_log(
            event_type=models.AuthEventType.password_reset_requested,
            email=user.email,
            user_id=user.id,
        )
        response = {"message": "If the email exists, a reset link has been sent."}
        if settings.EXPOSE_RESET_DEBUG_TOKEN:
            response["debug_token"] = raw_token
        return response

    def reset_password(self, payload: schemas.ResetPasswordRequest) -> None:
        if not password_meets_policy(payload.new_password):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Password must contain upper, lower, number, and special character "
                    f"with minimum length {settings.PASSWORD_MIN_LENGTH}"
                ),
            )

        token_row = self.repo.get_active_reset_token(hash_token(payload.token))
        if not token_row or token_row.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        user = self.db.query(models.User).filter(models.User.id == token_row.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.hashed_password = hash_password(payload.new_password)
        token_row.is_used = True
        self.repo.revoke_all_user_refresh_tokens(user.id)
        self.db.commit()

        self.repo.create_auth_audit_log(
            event_type=models.AuthEventType.password_reset_completed,
            email=user.email,
            user_id=user.id,
        )

    def _issue_token_pair(
        self,
        user: models.User,
        ip_address: str | None,
        user_agent: str | None,
    ) -> schemas.Token:
        access_token = create_access_token(subject=user.email, role=user.role.value)
        refresh_token = generate_secure_token()
        self.repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else None,
        )
        return schemas.Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            role=user.role,
        )
