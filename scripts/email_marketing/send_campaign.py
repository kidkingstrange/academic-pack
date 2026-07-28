#!/usr/bin/env python3
"""
Scale Group Campaign Sender Engine
Sends personalized, value-driven email campaigns via SMTP with rate limiting,
retry with exponential backoff, resumable logging, --dry-run, and --test flags.
"""
import os
import sys
import time
import csv
import json
import uuid
import smtplib
import argparse
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from jinja2 import Environment, FileSystemLoader

# Local imports
from loader import get_clean_subscriber_list
from scraper import parse_catalog_from_home_js

# Directory Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
PRODUCTS_PATH = os.path.join(BASE_DIR, "products.json")
LOG_PATH = os.path.join(BASE_DIR, "campaign_log.csv")
DRY_RUN_DIR = os.path.join(BASE_DIR, "dry_run_output")

# Campaign Lead Content Strategy
CAMPAIGN_THEMES = {
    "Sales & Marketing": {
        "subject": "Close high-ticket clients in DMs & WhatsApp",
        "preheader": "Copy-paste scripts & ad playbooks delivered instantly to your phone.",
        "lead_headline": "How Top Operators Close High-Ticket Clients via DM",
        "lead_story": "Closing high-ticket clients isn't about pushing hard — it's about structured conversation frameworks. Below are step-by-step masterclass books with copy-paste scripts, objection-handling templates, and ad blueprints you can access immediately."
    },
    "Business & Wealth": {
        "subject": "Build a business that runs without you",
        "preheader": "SOP blueprints & upfront cash flow playbooks (Instant Access).",
        "lead_headline": "Systematize Operations & Preserve Cash Flow",
        "lead_story": "A scalable business relies on documented SOPs and upfront cash flow models instead of manual firefighting. Below are practical masterclass books with exact frameworks to structure your enterprise."
    },
    "Career Acceleration": {
        "subject": "How to negotiate your next promotion & raise",
        "preheader": "Executive positioning & salary negotiation playbooks.",
        "lead_headline": "Executive Positioning & Promotion Frameworks",
        "lead_story": "Promotions aren't given for hard work alone — they require strategic visibility and ROI proof. Access these masterclass books to master workplace negotiation and leadership positioning."
    },
    "Mindset & Health": {
        "subject": "Double daily output without burnout",
        "preheader": "Deep work protocols & stress recovery playbooks.",
        "lead_headline": "Deep Work Stamina & Stress Recovery Systems",
        "lead_story": "Peak productivity requires structured deep-work blocks and nervous system recovery. Below are actionable masterclass books to eliminate overthinking and build unshakeable execution routines."
    },
    "Education & Mastery": {
        "subject": "Score high in any exam with less study hours",
        "preheader": "High-yield active recall & study tracker playbooks.",
        "lead_headline": "High-Yield Exam Preparation & Skill Mastery",
        "lead_story": "Studying 8 hours blindly produces far fewer results than 2 hours of active recall. Access these step-by-step study books to master complex topics and score top marks."
    }
}

def load_products():
    if not os.path.exists(PRODUCTS_PATH):
        return parse_catalog_from_home_js()
    with open(PRODUCTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_already_sent_emails():
    if not os.path.exists(LOG_PATH):
        return set()
    sent = set()
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") == "SUCCESS":
                sent.add(row.get("email", "").strip().lower())
    return sent

def log_send(email, name, status, msg_id="", error_msg=""):
    file_exists = os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "email", "name", "status", "message_id", "error"])
        writer.writerow([
            datetime.now().isoformat(),
            email,
            name,
            status,
            msg_id,
            error_msg
        ])

def render_email_content(recipient_name, recipient_email, selected_products, theme_info):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    html_template = env.get_template("campaign_email.html")
    txt_template = env.get_template("campaign_email.txt")

    unsubscribe_url = f"https://edgepack.thescaleconference.com/unsubscribe?email={recipient_email}"

    context = {
        "subject": theme_info["subject"],
        "preheader_text": theme_info["preheader"],
        "recipient_name": recipient_name,
        "lead_headline": theme_info["lead_headline"],
        "lead_story": theme_info["lead_story"],
        "products": selected_products,
        "unsubscribe_url": unsubscribe_url
    }

    html_content = html_template.render(**context)
    txt_content = txt_template.render(**context)
    return html_content, txt_content, unsubscribe_url

def send_smtp_email(to_email, to_name, subject, html_content, txt_content, unsubscribe_url):
    smtp_host = os.environ.get("SMTP_HOST", "mail.privateemail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ.get("SMTP_USER", "itoya@thescaleconference.com")
    smtp_pass = os.environ.get("SMTP_PASSWORD") or os.environ.get("SMTP_PASS", "")
    from_email = os.environ.get("FROM_EMAIL", "Scale Group <itoya@thescaleconference.com>")

    if not smtp_pass:
        raise ValueError("SMTP_PASSWORD environment variable is missing! Please export SMTP_PASSWORD.")

    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg_id = make_msgid(domain="thescaleconference.com")
    msg["Message-ID"] = msg_id
    msg["Reply-To"] = "itoya@thescaleconference.com"
    msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"

    msg.attach(MIMEText(txt_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # Connect to SSL/TLS SMTP
    if smtp_port == 465:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
        server.starttls()

    server.login(smtp_user, smtp_pass)
    server.sendmail(smtp_user, [to_email], msg.as_string())
    server.quit()

    return msg_id

def run_campaign(dry_run=False, test_email=None, category="Sales & Marketing", limit=4, batch_size=50, pause_seconds=60):
    all_products = load_products()
    
    # Filter products by category or select top picks
    matching_products = [p for p in all_products if category.lower() in p["category"].lower()]
    if not matching_products:
        matching_products = all_products

    selected_products = matching_products[:min(limit, 6)]
    theme_info = CAMPAIGN_THEMES.get(category, list(CAMPAIGN_THEMES.values())[0])

    print("\n" + "="*60)
    print(f" 🚀 SCALE GROUP EMAIL CAMPAIGN ENGINE")
    print("="*60)
    print(f" Theme: {category}")
    print(f" Subject Line: \"{theme_info['subject']}\"")
    print(f" Featured Products: {len(selected_products)} items")
    print(f" Mode: {'DRY RUN (No emails sent)' if dry_run else ('TEST SEND to ' + test_email if test_email else 'FULL CAMPAIGN')}")
    print("="*60 + "\n")

    if test_email:
        recipients = [{"email": test_email.strip().lower(), "name": "Tester"}]
    else:
        recipients = get_clean_subscriber_list()

    already_sent = get_already_sent_emails()
    pending_recipients = [r for r in recipients if r["email"] not in already_sent]

    print(f"[Campaign] Target Subscribers: {len(recipients)} | Pending: {len(pending_recipients)} | Already Sent: {len(already_sent)}")

    if not pending_recipients:
        print("[Campaign] All recipients have already received this campaign. Exiting.")
        return

    if dry_run:
        os.makedirs(DRY_RUN_DIR, exist_ok=True)
        for idx, sub in enumerate(pending_recipients[:3]):
            html_out, txt_out, _ = render_email_content(sub["name"], sub["email"], selected_products, theme_info)
            html_file = os.path.join(DRY_RUN_DIR, f"preview_{idx+1}_{sub['email'].replace('@', '_at_')}.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_out)
            print(f"[Dry-Run] Saved preview HTML -> {html_file}")
        print("\n✅ Dry-Run Complete! Check the HTML preview files in 'dry_run_output/'.")
        return

    # Real Sending Loop with Rate Limiting
    sent_count = 0
    for idx, sub in enumerate(pending_recipients, 1):
        email = sub["email"]
        name = sub["name"]

        html_out, txt_out, unsub_url = render_email_content(name, email, selected_products, theme_info)

        # Retry logic up to 3 times
        success = False
        msg_id = ""
        last_err = ""

        for attempt in range(1, 4):
            try:
                msg_id = send_smtp_email(email, name, theme_info["subject"], html_out, txt_out, unsub_url)
                success = True
                break
            except Exception as err:
                last_err = str(err)
                print(f" [Attempt {attempt}/3 Failed for {email}]: {last_err}")
                time.sleep(2 * attempt)

        if success:
            sent_count += 1
            log_send(email, name, "SUCCESS", msg_id)
            print(f"[{idx}/{len(pending_recipients)}] ✅ Sent to {name} <{email}> (MsgID: {msg_id})")
        else:
            log_send(email, name, "FAILED", "", last_err)
            print(f"[{idx}/{len(pending_recipients)}] ❌ Failed sending to {email}: {last_err}")

        # Batch Pause Rate Limiting
        if idx % batch_size == 0 and idx < len(pending_recipients):
            print(f"\n[Rate Limit] Sent batch of {batch_size} emails. Pausing for {pause_seconds} seconds...\n")
            time.sleep(pause_seconds)

    print(f"\n🎉 Campaign complete! Total sent in this run: {sent_count}/{len(pending_recipients)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scale Group Email Campaign Sender")
    parser.add_argument("--dry-run", action="store_true", help="Render emails to HTML locally without sending")
    parser.add_argument("--test", type=str, help="Send single test email to specified address")
    parser.add_argument("--category", type=str, default="Sales & Marketing", help="Product category theme")
    parser.add_argument("--limit", type=int, default=4, help="Max products to feature")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch rate limit")
    parser.add_argument("--pause", type=int, default=60, help="Pause seconds between batches")

    args = parser.parse_args()
    run_campaign(
        dry_run=args.dry_run,
        test_email=args.test,
        category=args.category,
        limit=args.limit,
        batch_size=args.batch_size,
        pause_seconds=args.pause
    )
