"""Seed script: create default super admin account on first run."""

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import User, UserRole
from app.security import hash_password

Base.metadata.create_all(bind=engine)


def seed() -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if existing:
            print(f"Admin already exists: {settings.ADMIN_EMAIL}")
            return

        admin = User(
            name="RSS Super Admin",
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            role=UserRole.super_admin,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Admin user created: {settings.ADMIN_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
