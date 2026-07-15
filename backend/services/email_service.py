"""
Email service — send via SMTP using Jinja2 templates.
"""
import asyncio
import re
import html
import smtplib
import ssl
import threading
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


SMTP_TIMEOUT_SECONDS = 30

# ── Persistent SMTP connection ──────────────────────────────────────────────
# A burst of ~13 near-simultaneous signups on 2026-07-13 preceded welcome-
# email delivery breaking almost completely for the following ~40 hours
# (near-zero successful sends, everything else timing out). The likely
# trigger: this module used to open a brand-new connection AND log in fresh
# for every single email, even when processing many in one
# process_email_queue() batch — exactly the connection/login burst pattern
# mail providers throttle. Now one connection is opened per batch and reused
# across every item in it, validated with NOOP before each send and
# transparently reconnected if it's gone stale. process_email_queue() already
# serializes all sends via _email_queue_lock, so this reuse is safe without
# additional locking, but _smtp_lock guards against any future caller that
# might send outside that path.
_smtp_connection = None
_smtp_lock = threading.Lock()


def _open_smtp_connection():
    context = ssl.create_default_context()
    if settings.SMTP_PORT == 465:
        conn = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=SMTP_TIMEOUT_SECONDS)
    else:
        conn = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS)
        conn.ehlo()
        conn.starttls(context=context)
    conn.login(settings.SMTP_USER, settings.SMTP_PASS)
    return conn


def _get_smtp_connection():
    """Returns a live SMTP connection, reusing the existing one if it still
    answers NOOP, otherwise closing it and logging in fresh exactly once."""
    global _smtp_connection
    if _smtp_connection is not None:
        try:
            status = _smtp_connection.noop()[0]
            if status == 250:
                return _smtp_connection
        except Exception:
            pass
        try:
            _smtp_connection.close()
        except Exception:
            pass
        _smtp_connection = None

    _smtp_connection = _open_smtp_connection()
    return _smtp_connection


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

    with _smtp_lock:
        try:
            server = _get_smtp_connection()
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        except Exception:
            # The reused connection may have died mid-batch (server-side
            # idle timeout, network blip) — drop it and retry once with a
            # fresh login rather than failing this send outright.
            global _smtp_connection
            try:
                _smtp_connection.close()
            except Exception:
                pass
            _smtp_connection = None
            server = _get_smtp_connection()
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


async def send_welcome_email(name: str, email: str, token: str, unsubscribe_token: str = "", delayed: bool = False):
    """Send welcome + download access email after successful payment.

    delayed=True adds a brief, honest acknowledgment of a delivery delay —
    used only for the one-time recovery resend of emails that failed
    before the email-queue concurrency fix; never set on a normal
    first-attempt send.
    """
    html = render_template("welcome.html", {
        "name": name,
        "library_url": f"{settings.APP_URL}/library?token={token}",
        "whatsapp_url": settings.WHATSAPP_COMMUNITY_LINK,
        "app_name": settings.APP_NAME,
        "app_url": settings.APP_URL,
        "unsubscribe_token": unsubscribe_token,
        "delayed": delayed,
    })
    subject = (
        f"Sorry for the wait — your Academic Comeback Package is ready, {name}!"
        if delayed else
        f"🎉 Your Academic Comeback Package is ready, {name}!"
    )
    return await send_email(email, subject, html)


async def send_affiliate_welcome_email(name: str, email: str, code: str, referral_link: str, dashboard_link: str):
    """Send confirmation + referral/dashboard links after affiliate registration."""
    html = render_template("affiliate_welcome.html", {
        "name": name,
        "code": code,
        "referral_link": referral_link,
        "dashboard_link": dashboard_link,
        "app_name": settings.APP_NAME,
        "app_url": settings.APP_URL,
    })
    return await send_email(email, f"You're in — here's your referral link, {name}", html)


async def send_affiliate_nudge_email(name: str, email: str, referral_link: str):
    """One-time reminder for an affiliate who downloaded marketing
    materials but hasn't clicked their own link within 3 days. Sent
    exactly once per affiliate — see workers/affiliate_nudge_scheduler.py."""
    html = render_template("affiliate_nudge.html", {
        "name": name,
        "referral_link": referral_link,
        "app_name": settings.APP_NAME,
        "app_url": settings.APP_URL,
    })
    return await send_email(email, f"Ready to share your link, {name}?", html)


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
