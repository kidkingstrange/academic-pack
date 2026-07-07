"""
Email service — send via SMTP using Jinja2 templates.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..config import get_settings

settings = get_settings()

# Jinja2 template environment
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_template(template_name: str, context: dict) -> str:
    tpl = env.get_template(template_name)
    return tpl.render(**context)


async def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email via SMTP. Supports both SSL (465) and STARTTLS (587)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        context = ssl.create_default_context()

        if settings.SMTP_PORT == 465:
            # SSL connection
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        else:
            # STARTTLS connection (port 587)
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"📧 Email error: {e}")
        return False


async def send_welcome_email(name: str, email: str, token: str, unsubscribe_token: str = ""):
    """Send welcome + download access email after successful payment."""
    html = render_template("welcome.html", {
        "name": name,
        "library_url": f"{settings.APP_URL}/api/auth/magic?token={token}&redirect=/library",
        "whatsapp_url": settings.WHATSAPP_COMMUNITY_LINK,
        "app_name": settings.APP_NAME,
        "app_url": settings.APP_URL,
        "unsubscribe_token": unsubscribe_token,
    })
    await send_email(email, f"🎉 Your Academic Comeback Package is ready, {name}!", html)


async def send_sequence_email(name: str, email: str, template_name: str, subject: str, unsubscribe_token: str = "", context: dict = {}):
    """Send a scheduled sequence email."""
    merged = {
        "name": name,
        "email": email,
        "app_url": settings.APP_URL,
        "unsubscribe_token": unsubscribe_token,
        **context
    }
    html = render_template(f"sequence/{template_name}", merged)
    return await send_email(email, subject, html)
