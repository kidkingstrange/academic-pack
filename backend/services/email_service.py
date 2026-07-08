"""
Email service — send via SMTP using Jinja2 templates.
"""
import asyncio
import re
import html
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


def html_to_text(html_content: str) -> str:
    """Strip tags and convert html body to plain text for spam filter compliance."""
    text = re.sub(r"<(style|script)[^>]*?>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]*?>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return html.unescape(text)


def render_template(template_name: str, context: dict) -> str:
    tpl = env.get_template(template_name)
    return tpl.render(**context)


SMTP_TIMEOUT_SECONDS = 15


def _send_sync(to_email: str, subject: str, html_body: str) -> None:
    """Blocking SMTP send — must only ever run in a worker thread, never
    directly on the asyncio event loop (see send_email())."""
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    # Attach plain text part first, then HTML part for standard alternative MIME compliance
    plain_text = html_to_text(html_body)
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()

    if settings.SMTP_PORT == 465:
        # SSL connection
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
    else:
        # STARTTLS connection (port 587)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())


async def send_email(to_email: str, subject: str, html_body: str) -> tuple:
    """Send an email via SMTP. Returns (success: bool, error_message: str|None).

    Runs the actual send in a worker thread via asyncio.to_thread(), not
    directly on the event loop — smtplib is blocking, and a single hung
    SMTP connection previously froze the entire server (every request,
    not just email sends) since nothing else could run on the one event
    loop while it waited. The timeout above is a second layer, in case a
    connection hangs somewhere smtplib's own timeout doesn't cover.
    """
    try:
        await asyncio.to_thread(_send_sync, to_email, subject, html_body)
        return (True, None)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        print(f"📧 Email error to {to_email}: {error_msg}")
        return (False, error_msg)


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
    return await send_email(email, f"🎉 Your Academic Comeback Package is ready, {name}!", html)


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
