# FIX PROMPT — Welcome emails failing & customers not receiving working library access links

## ROLE
You are a senior backend engineer. Fix a specific, active production problem in this FastAPI + MongoDB (Motor) + PrivateEmail-SMTP application: **after a customer buys, the welcome/access email either never arrives or arrives with a dead "Access Your Library" link.** Do not refactor unrelated code. Preserve all currently-working behavior. Verify by real execution wherever possible.

## STACK / KEY FILES
- Config: `backend/config.py` (Pydantic settings; `get_settings()` has a `RENDER_EXTERNAL_URL` override).
- Payment completion (queues the welcome email): `backend/services/payment_completion.py::complete_payment`.
- Email worker: `backend/workers/email_scheduler.py` (`process_email_queue`, `enqueue_sequence_for_subscriber`, `EMAIL_SEQUENCE`).
- Email send/render: `backend/services/email_service.py` (`send_welcome_email`, `send_sequence_email`, `send_email`, persistent SMTP connection).
- Templates: `backend/templates/emails/welcome.html`, `base.html`.
- Verify endpoint used by the browser: `backend/routes/payments.py::verify_payment`; self-service recovery: `backend/routes/library.py::resend_library_link`.
- Live config observed in `.env`: `APP_URL=http://127.0.0.1:8000`, `APP_ENV=development`, SMTP = `mail.privateemail.com:465`, single account `itoya@thescaleconference.com`, `FROM_EMAIL` on the same domain.

---

## PHASE 0 — CONFIRM BEFORE CHANGING
- Inspect the files above and confirm both root causes still hold: (a) `library_url` is `f"{settings.APP_URL}/library?token={token}"` in `email_service.py`, and `APP_URL` resolves to `127.0.0.1` unless `RENDER_EXTERNAL_URL` is set; (b) welcome emails and the 52-email sequence all send through one PrivateEmail account/connection.
- Inspect the running deployment to determine what `APP_URL`/`APP_ENV`/`RENDER_EXTERNAL_URL` actually resolve to in production, and query the `email_queue` collection for `status: "failed"`/`"retry"` items and read their `error` fields to capture the real SMTP rejection text (daily-limit, auth, rate-limit, etc.). Record findings before editing.
- Do not change anything in Phase 0.

---

## FIX GROUP A — Access links point to localhost (delivered emails are useless)

### A1. Stop shipping `127.0.0.1` (or any localhost) in customer-facing links
- **Problem:** The welcome email's "Access Your Library" button, the sequence-email links, and the unsubscribe link are all built from `settings.APP_URL`. In the running config `APP_URL=http://127.0.0.1:8000`, so customers receive a link to their own machine and cannot reach their library.
- **Location:** `backend/config.py` (`APP_URL`, `get_settings` override), `backend/services/email_service.py:151` (`library_url`) and lines building `app_url` for templates, `backend/templates/emails/base.html` (unsubscribe link).
- **Root cause:** `APP_URL` defaults to localhost and is only overridden when `RENDER_EXTERNAL_URL` is present; the deployed environment is running with the localhost value (and `APP_ENV=development`).
- **Required change:**
  1. Set the correct production values in the deployment environment: `APP_URL=https://<real-production-domain>` and `APP_ENV=production` (do this in the host/Render env, not by hardcoding). Keep `.env` for local dev only.
  2. Add a **startup guard** in `backend/main.py` mirroring the existing `check_admin_password_rotated` / `check_cors_configured_for_production` pattern: if `APP_ENV == "production"` and `APP_URL` contains `localhost`/`127.0.0.1` (or is empty), **hard-fail startup** with a clear message — a localhost `APP_URL` silently breaks every access link, so it must never boot in production.
  3. Keep the `RENDER_EXTERNAL_URL` override, but confirm it actually resolves in the running platform; the guard above is the backstop when it doesn't.
- **Expected behaviour:** Every emailed link (`/library?token=…`, sequence links, `/unsubscribe`) points to the real public domain and opens the customer's library.
- **Constraints:** Do not break local development (localhost must still work when `APP_ENV=development`). Do not change the token format or the `/library` route contract.
- **Verification:** In a production-like env, complete a test purchase and confirm the delivered link is `https://<domain>/library?token=…` and loads the library. Start the app with `APP_ENV=production` + a localhost `APP_URL` and confirm it refuses to boot. Confirm local dev still starts and links to localhost.

### A2. Make on-screen access the primary path; email is recovery (reduce dependence on email delivery)
- **Problem:** Customers effectively depend on the email to reach their books, so any mail failure = no access.
- **Location:** `backend/routes/payments.py::verify_payment` (already returns `token` + `magic_link`), `frontend/welcome.html`, `frontend/js/checkout.js` (redirects to `/welcome?token=…`), `backend/routes/library.py::resend_library_link`.
- **Root cause:** Access is treated as email-delivered rather than immediately shown after payment.
- **Required change:** Ensure the post-payment `/welcome` page prominently displays the working library link/button using the token already returned by `verify_payment` (no email needed to reach the library), and that the "lost your link? resend" recovery (`resend_library_link`) is discoverable. Do not remove the welcome email — it remains the durable backup and community/sequence entry point.
- **Expected behaviour:** A buyer reaches their library from the success screen even if the email is delayed or fails; the email becomes a convenience/backup, not a single point of failure.
- **Constraints:** Keep the storage-blocked in-app-browser handling in `checkout.js` (URL-token fallback) intact. Keep `resend_library_link` generic (no user enumeration).
- **Verification:** Simulate a successful verify, confirm `/welcome?token=…` shows a working library link with the email disabled; confirm resend recovery works.

---

## FIX GROUP B — Welcome emails fail to send (single PrivateEmail account throttled)

### B1. Separate transactional (welcome/access) from bulk (52-email sequence) so a backlog can't throttle the one email that matters
- **Problem:** On each purchase the app queues the welcome email **and** the full 52-email curriculum (day-0 email due immediately). All flow through one PrivateEmail account/connection. PrivateEmail enforces daily-send and connection rate limits; under the combined volume the account gets throttled and the transactional welcome email fails (then retries 10× and is marked `failed`).
- **Location:** `backend/services/payment_completion.py` (queues welcome + `enqueue_sequence_for_subscriber`), `backend/workers/email_scheduler.py::process_email_queue`, `backend/services/email_service.py` (single connection/account).
- **Root cause:** Transactional and bulk mail share one throttled sender with no prioritization or pacing.
- **Required change:** Implement at least one of these, preferring the least new complexity that reliably fixes deliverability:
  1. **Prioritize transactional email:** in `process_email_queue`, process `kind == "welcome"` / `affiliate_welcome` (and other access-granting mail) **before** `kind == "sequence"`, so the welcome always sends even when the daily budget is nearly exhausted.
  2. **Pace sends to the provider's limits:** add throttling (a max send-rate / per-run cap and small inter-send delay) so bursts don't trip PrivateEmail's connection/rate limits — the incident documented in-code was caused by exactly this.
  3. **Route transactional mail through a reliable transactional sender** (a dedicated transactional email provider, or at minimum a **separate SMTP account** reserved for welcome/access mail, distinct from the bulk-sequence account). This is a justified case for a provider/account change because deliverability of the paid product's access email is business-critical. If you add a provider, keep the existing SMTP path as fallback and gate the choice behind config.
- **Expected behaviour:** The welcome/access email sends reliably and promptly after purchase regardless of how large the sequence backlog is; provider rate limits are respected instead of tripped.
- **Constraints:** Preserve the existing atomic `find_one_and_update` claim, the `asyncio.Lock` serialization, exponential backoff, startup "rescue stuck sending" job, and hourly health check. Do not reintroduce the per-email connect+login pattern that caused the original 40-hour outage. Keep the sequence emails working.
- **Verification:** Queue a welcome plus a large sequence backlog and confirm the welcome is sent first and succeeds; run a burst of N purchases and confirm no throttling failures and that pacing stays within the provider's documented limits; inspect `email_queue` for zero `failed` welcome items after the run.

### B2. Confirm SMTP identity is deliverable (defensive check)
- **Problem:** Deliverability also fails if the sending domain isn't authenticated, causing silent drops/spam-foldering that look like "failures."
- **Location:** `.env` SMTP settings; DNS for `thescaleconference.com` (SPF/DKIM/DMARC) — operational, outside code.
- **Root cause:** `From`/domain authentication gaps reduce inbox delivery even when SMTP accepts the message.
- **Required change:** Confirm `FROM_EMAIL`/`SMTP_USER` are the same authenticated domain (they currently are — `itoya@thescaleconference.com`), and verify SPF/DKIM/DMARC are configured for `thescaleconference.com` at the DNS/provider level. No code change unless a mismatch is found; if `FROM_EMAIL` and `SMTP_USER` ever diverge, align them.
- **Expected behaviour:** Messages authenticate and land in the inbox, not spam.
- **Constraints:** Do not change the sending identity away from the authenticated domain.
- **Verification:** Send a test welcome to a Gmail/Outlook address and confirm inbox placement + passing SPF/DKIM/DMARC in the message headers.

### B3. Make failures visible instead of silent
- **Problem:** When a welcome email exhausts retries it is marked `failed` and the customer silently never hears from you.
- **Location:** `backend/workers/email_scheduler.py` (retry/`failed` handling, existing `check_email_health`).
- **Root cause:** No alert when transactional access mail dead-letters.
- **Required change:** Extend the existing health check (or add a targeted alert) to notify the admin (reuse `send_email` to `ADMIN_EMAIL`, the same pattern used for webhook-flagging) when any `kind == "welcome"` item reaches `status: "failed"`, so a paying customer without access is caught immediately and can be resent via the existing admin "resend access email" endpoint.
- **Expected behaviour:** A failed access email raises an operator alert the same day, not days later.
- **Constraints:** Don't spam alerts — summarize/coalesce. Keep the existing hourly health check behavior.
- **Verification:** Force a welcome-email failure and confirm an admin alert fires and the admin resend endpoint recovers the customer.

---

## COMPLETION CRITERIA / DEFINITION OF DONE
- [ ] Phase 0 findings recorded, including the actual `failed`-queue SMTP error text and the real resolved `APP_URL` in production.
- [ ] Production env set to real `APP_URL` (https domain) + `APP_ENV=production`; app hard-fails to boot if `APP_ENV=production` with a localhost/empty `APP_URL`; local dev still works.
- [ ] A delivered welcome email's "Access Your Library" link opens the real production library; unsubscribe and sequence links also use the real domain.
- [ ] Post-payment `/welcome` screen shows a working library link without needing the email; `resend_library_link` recovery works.
- [ ] Welcome/transactional email is prioritized and/or paced (or routed via a reliable transactional sender/separate account) so it sends reliably regardless of sequence backlog; no throttling failures under a purchase burst; provider limits respected.
- [ ] SPF/DKIM/DMARC verified for the sending domain; `FROM_EMAIL` and `SMTP_USER` aligned.
- [ ] Admin is alerted when any welcome email dead-letters.
- [ ] Preserved intact: atomic email-queue claim, `asyncio.Lock`, exponential backoff, startup rescue, hourly health check, the idempotent `complete_payment` contract, the no-per-email-login SMTP design, and the in-app-browser URL-token fallback.
- [ ] Verified by execution: a real test purchase end-to-end delivers a working link, reaches the library from the success screen, and leaves zero `failed` welcome items in `email_queue`.
