import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def is_configured(self) -> bool:
        return bool(settings.SMTP_ENABLED and settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)

    def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
    ) -> tuple[bool, str | None]:
        if not self.is_configured():
            return False, "SMTP is disabled or not configured"

        message = EmailMessage()
        if settings.SMTP_FROM_NAME:
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        else:
            message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        try:
            if settings.SMTP_USE_SSL:
                smtp_client = smtplib.SMTP_SSL(
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                    timeout=settings.SMTP_TIMEOUT_SECONDS,
                )
            else:
                smtp_client = smtplib.SMTP(
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                    timeout=settings.SMTP_TIMEOUT_SECONDS,
                )

            with smtp_client as smtp:
                smtp.ehlo()
                if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                    smtp.starttls()
                    smtp.ehlo()
                if settings.SMTP_USERNAME:
                    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(message)
            return True, None
        except Exception as exc:
            logger.exception("SMTP delivery failed for %s", to_email)
            return False, str(exc)
