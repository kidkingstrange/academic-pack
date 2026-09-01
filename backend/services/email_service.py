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


def render_template(template_name: str, context: dict = None, **kwargs) -> str:
    tpl = env.get_template(template_name)
    merged = {}
    if context:
        merged.update(context)
    if kwargs:
        merged.update(kwargs)
    return tpl.render(**merged)


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


async def send_welcome_email(
    name: str,
    email: str,
    token: str,
    unsubscribe_token: str = "",
    delayed: bool = False,
    affiliate_code: str = None,
    referral_link: str = None,
    dashboard_link: str = None,
    recruiter_link: str = None,
):
    """Send welcome + download access email after successful payment."""
    html = render_template("welcome.html", {
        "name": name,
        "library_url": f"{settings.APP_URL}/library?token={token}",
        "whatsapp_url": settings.WHATSAPP_COMMUNITY_LINK,
        "app_name": settings.APP_NAME,
        "app_url": settings.APP_URL,
        "unsubscribe_token": unsubscribe_token,
        "delayed": delayed,
        "affiliate_code": affiliate_code,
        "referral_link": referral_link,
        "dashboard_link": dashboard_link,
        "recruiter_link": recruiter_link,
    })
    subject = (
        f"Sorry for the wait — your Academic Comeback Package is ready, {name}!"
        if delayed else
        f"🎉 Your Academic Comeback Package is ready, {name}!"
    )
    return await send_email(email, subject, html)



async def send_affiliate_welcome_email(
    name: str, email: str, code: str, referral_link: str, dashboard_link: str, affiliate_invite_link: str = None
):
    """Send confirmation + referral/dashboard links after affiliate registration."""
    html = render_template("affiliate_welcome.html", {
        "name": name,
        "code": code,
        "referral_link": referral_link,
        "affiliate_invite_link": affiliate_invite_link or f"{settings.APP_URL}/affiliate/register?invite={code}",
        "dashboard_link": dashboard_link,
        "app_name": settings.APP_NAME,
        "app_url": settings.APP_URL,
    })
    return await send_email(email, f"Welcome to the Affiliate Program — Your Links & ₦10,000 Bonus Challenge, {name}", html)


async def send_affiliate_direct_milestone_email(
    name: str,
    email: str,
    code: str,
    bonus_amount: float,
    sales_count: int,
    dashboard_link: str,
    is_transferred: bool = False,
    transfer_reference: str = "",
    bank_name: str = "",
    account_number: str = "",
):
    """Send celebratory email when an affiliate reaches the 10-sale milestone."""
    html = render_template("affiliate_direct_milestone.html", {
        "name": name,
        "code": code,
        "bonus_amount": bonus_amount,
        "sales_count": sales_count,
        "dashboard_link": dashboard_link,
        "is_transferred": is_transferred,
        "transfer_reference": transfer_reference,
        "bank_name": bank_name,
        "account_number": account_number,
        "app_name": settings.APP_NAME,
        "app_url": settings.APP_URL,
    })
    subject = (
        f"🏆 ₦{int(bonus_amount):,} Transferred to Your Bank Account, {name}!"
        if is_transferred
        else f"🏆 CONGRATULATIONS: You Unlocked Your ₦{int(bonus_amount):,} Milestone Bonus, {name}!"
    )
    return await send_email(email, subject, html)


async def send_affiliate_parent_referral_bonus_email(
    name: str,
    email: str,
    code: str,
    subaffiliate_name: str,
    bonus_amount: float,
    dashboard_link: str,
    is_transferred: bool = False,
    transfer_reference: str = "",
    bank_name: str = "",
    account_number: str = "",
):
    """Send celebratory email when an invited affiliate reaches 10 sales, rewarding the parent recruiter."""
    html = render_template("affiliate_parent_referral_bonus.html", {
        "name": name,
        "code": code,
        "subaffiliate_name": subaffiliate_name,
        "bonus_amount": bonus_amount,
        "dashboard_link": dashboard_link,
        "is_transferred": is_transferred,
        "transfer_reference": transfer_reference,
        "bank_name": bank_name,
        "account_number": account_number,
        "app_name": settings.APP_NAME,
        "app_url": settings.APP_URL,
    })
    subject = (
        f"🎉 ₦{int(bonus_amount):,} Recruiter Bonus Transferred to Your Bank Account, {name}!"
        if is_transferred
        else f"🎉 Great News: You Earned a ₦{int(bonus_amount):,} Recruiter Bonus, {name}!"
    )
    return await send_email(email, subject, html)



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


async def send_welcome_failure_alert_email(failed_count: int, window_hours: int, failures: list):
    """
    Internal ops alert to ADMIN_EMAIL — not customer-facing, so no
    branded base.html template, just a plain readable summary. Fired by
    workers/email_delivery_alert_scheduler.py when failed welcome
    emails cross WELCOME_FAILURE_ALERT_THRESHOLD within a rolling
    window, so a systemic problem (like the SMTP concurrency bug) gets
    caught within a day instead of silently accumulating for weeks.
    """
    rows = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>{html.escape(f['email'] or '')}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{html.escape(f['name'] or '')}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{html.escape(f['error'] or '')}</td></tr>"
        for f in failures
    )
    html_body = f"""
    <div style="font-family:Arial,sans-serif;font-size:14px;color:#222">
      <p><strong>{failed_count} welcome emails have failed</strong> in the last {window_hours} hours.
      This usually means a systemic problem (SMTP, a bad template, a config issue) rather than isolated failures —
      each one blocks a paying customer from reaching their product.</p>
      <table style="border-collapse:collapse;width:100%;margin-top:12px">
        <tr style="background:#f5f4f0;text-align:left">
          <th style="padding:6px 10px">Email</th><th style="padding:6px 10px">Name</th><th style="padding:6px 10px">Error</th>
        </tr>
        {rows}
      </table>
      <p style="margin-top:16px">Check the Email Delivery tab in the admin dashboard for the full picture.</p>
    </div>
    """
    return await send_email(
        settings.ADMIN_EMAIL,
        f"⚠️ {failed_count} welcome emails failed in the last {window_hours}h",
        html_body,
    )


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


async def send_lead_magnet_welcome_email(name: str, email: str, ref_code: str, referral_link: str):
    """Send free cheat sheet deliverable + referral link after lead magnet opt-in."""
    html_body = render_template("welcome_lead_magnet.html", {
        "name": name,
        "ref_code": ref_code,
        "referral_link": referral_link,
        "app_name": settings.APP_NAME,
        "app_url": settings.APP_URL,
    })
    subject = "[FREE DOWNLOAD] Your 15-Minute DM Objection Matrix Cheat Sheet"
    return await send_email(email, subject, html_body)
