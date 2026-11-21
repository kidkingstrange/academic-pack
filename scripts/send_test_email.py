import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path
from dotenv import dotenv_values

def send_test(recipient: str = "daviditoyaa@gmail.com", preview_file: str = "direct_response_quitting.html"):
    env_vars = {}
    env_file = Path(".env")
    if env_file.exists():
        env_vars = dotenv_values(env_file)
    
    # Priority: os.environ -> .env file -> defaults
    smtp_host = os.environ.get("SMTP_HOST") or env_vars.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT") or env_vars.get("SMTP_PORT", 465))
    smtp_user = os.environ.get("SMTP_USER") or env_vars.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS") or env_vars.get("SMTP_PASS") or env_vars.get("SMTP_PASSWORD", "")
    from_email = os.environ.get("FROM_EMAIL") or env_vars.get("FROM_EMAIL", f"Scale Group <{smtp_user}>" if smtp_user else "Scale Group <no-reply@thescaleconference.com>")

    if not smtp_user or not smtp_pass:
        print("ERROR: Missing SMTP credentials.")
        print(f"SMTP_USER: {'SET' if smtp_user else 'MISSING'}")
        print(f"SMTP_PASS: {'SET' if smtp_pass else 'MISSING'}")
        return False, "SMTP_USER or SMTP_PASS is missing."

    preview_path = Path("frontend/email-previews") / preview_file
    if not preview_path.exists():
        return False, f"Preview file {preview_path} not found."

    html_content = preview_path.read_text(encoding="utf-8")
    
    # Simple plain text version
    plain_text = "This is a test email preview from Scale Group Marketing Engine.\nView HTML in an email client that supports HTML."

    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = recipient
    msg["Subject"] = "[TEST PREVIEW] Quitting The Handjob — The Neurochemical Reset Protocol"
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="thescaleconference.com")
    msg["List-Unsubscribe"] = f"<https://edgepack.thescaleconference.com/unsubscribe?email={recipient}>"

    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    print(f"Connecting to {smtp_host}:{smtp_port} as {smtp_user}...")
    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [recipient], msg.as_string())
        server.quit()
        print(f"SUCCESS: Test email successfully dispatched to {recipient}!")
        return True, "Delivered successfully."
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        print(f"FAILED: {err}")
        return False, err

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "daviditoyaa@gmail.com"
    send_test(target)
