# 📧 Scale Group Automated Email Marketing System

An automated, value-first, high-deliverability email marketing system designed for **Scale Group** (`edgepack.thescaleconference.com`).

---

## 🛠️ Architecture Components

1. **`scraper.py`**: Extracts product catalog (titles, prices, descriptions, images, landing URLs) from the catalog into `products.json`.
2. **`loader.py`**: Pulls subscriber list from database, validates email syntax, deduplicates, and filters against `unsubscribed.txt`.
3. **`templates/campaign_email.html` & `.txt`**: Responsive HTML & plain text campaign email templates with inline CSS and CAN-SPAM compliant footers.
4. **`send_campaign.py`**: Main CLI execution script supporting `--dry-run`, `--test <email>`, rate limiting (50 per batch, 60s pause), retry with backoff, and resumable logging in `campaign_log.csv`.
5. **`unsubscribe.py`**: Unsubscribe request handler that appends addresses to `unsubscribed.txt`.
6. **`schedule_campaign.py`**: Enforces frequency cap (max 1 campaign run per week) before executing.

---

## 🔑 Environment Setup

Ensure your `.env` file contains your SMTP credentials:

```env
SMTP_HOST=mail.privateemail.com
SMTP_PORT=465
SMTP_USER=itoya@thescaleconference.com
SMTP_PASSWORD=YOUR_SMTP_PASSWORD_HERE
FROM_EMAIL=Scale Group <itoya@thescaleconference.com>
```

---

## 🚀 Execution Commands

### 1. Re-run Product Scraper (Keep Catalog Fresh)
```bash
python3 scripts/email_marketing/scraper.py
```

### 2. Dry-Run Mode (Render HTML Locally for Review)
```bash
python3 scripts/email_marketing/send_campaign.py --dry-run
```
*Generates HTML previews in `scripts/email_marketing/dry_run_output/` without sending any network request.*

### 3. Send Single Test Email
```bash
python3 scripts/email_marketing/send_campaign.py --test recipient@example.com
```

### 4. Single-Command Full Campaign Launch
```bash
python3 scripts/email_marketing/send_campaign.py
```

### 5. Unsubscribe an Address
```bash
python3 scripts/email_marketing/unsubscribe.py customer@example.com
```

---

## 🛡️ Deliverability & Compliance Safeguards
- **Rate-Limiting**: Sends in batches of 50 with a 60-second cooldown pause.
- **Resumable Logging**: Logged in `campaign_log.csv`; re-running skips already-sent recipients.
- **Headers**: Includes valid `Message-ID`, `List-Unsubscribe`, and `From` / `Reply-To` headers.
- **CAN-SPAM**: Every email contains a physical business address and functional unsubscribe link.
