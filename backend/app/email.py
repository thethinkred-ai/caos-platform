import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .config import get_settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        # Without SMTP a registration would strand the account behind an
        # email that never arrives. LOG_UNSENT_EMAILS surfaces the message
        # (and its verification link) in the log so local setups still work.
        if settings.log_unsent_emails:
            logger.warning("EMAIL NOT SENT (SMTP not configured)\nTo: %s\nSubject: %s\n%s", to, subject, body)
        return
    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html", "utf-8"))
    if settings.smtp_port == 465:
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        server.starttls()
    try:
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, to, msg.as_string())
    finally:
        server.quit()
