"""
Seed script — creates an admin user on first run.
Run: python -m app.seed
"""
from app.database import SessionLocal, engine, Base
from app.models import User, UserRole
from app.security import hash_password
from app.config import settings

Base.metadata.create_all(bind=engine)


def seed():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if existing:
            print(f"Admin already exists: {settings.ADMIN_EMAIL}")
            return

        admin = User(
            name="RSS Admin",
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"✅ Admin user created: {settings.ADMIN_EMAIL} / {settings.ADMIN_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
