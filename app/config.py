from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "RSS Attendance System"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"

    SECRET_KEY: str = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET_KEY_MIN_32_CHARS"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_MIN_LENGTH: int = 8
    MAX_ATTENDANCE_HISTORY_LIMIT: int = 180
    ENABLE_DOCS: bool = True
    EXPOSE_RESET_DEBUG_TOKEN: bool = False
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "RSS Attendance System"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 20
    ENABLE_ATTENDANCE_REMINDER_SCHEDULER: bool = True
    ATTENDANCE_REMINDER_HOUR: int = 9
    ATTENDANCE_REMINDER_MINUTE: int = 0
    ATTENDANCE_REMINDER_TIMEZONE: str = "Asia/Kolkata"

    MYSQL_HOST: str = "db"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_DATABASE: str = "rss_db"
    DATABASE_URL: str | None = None

    ADMIN_EMAIL: str = "admin@rss.com"
    ADMIN_PASSWORD: str = "Admin@123"

    CORS_ORIGINS: str = Field(
        default="http://localhost,http://localhost:80,http://localhost:8000,http://127.0.0.1,http://127.0.0.1:8000"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @staticmethod
    def parse_cors_origins(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("[") and stripped.endswith("]"):
                stripped = stripped[1:-1]
            return [item.strip().strip('"').strip("'") for item in stripped.split(",") if item.strip()]
        return []

    @property
    def cors_origins_list(self) -> list[str]:
        return self.parse_cors_origins(self.CORS_ORIGINS)

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
