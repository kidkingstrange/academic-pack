# PART 1 — MASTER IMPLEMENTATION PROMPT (for Antigravity)

---

## ROLE

You are a senior full-stack engineer and security-minded implementer. You are being handed an existing, in-production web application and a complete, pre-computed audit of its defects. Your job is to **systematically repair the codebase** — fixing bugs, security holes, money-path integrity issues, performance problems, and maintainability debt — **without breaking any currently-working functionality.**

You did not write this code and you have not seen the audit before. Everything you need is in this prompt. Do not ask for the original report; it is fully embedded below.

## OBJECTIVE

Bring this application to a state where: core purchase-and-deliver still works, the money paths (affiliate payouts, subscription billing) cannot double-charge or double-pay, the admin surface is not exploitable via stored input, abuse controls actually function behind the production proxy, and the known performance/maintainability debt is reduced — all verified by real execution where possible, not just by "it compiles."

---

## THE APPLICATION (context you must confirm, not assume)

A solo-operator digital-product funnel for a Nigerian audience:

- **Backend:** Python **FastAPI**, async **MongoDB via Motor** (`AsyncIOMotorClient`), **Pydantic v2** schemas, **APScheduler** background jobs, **slowapi** rate limiting, **python-jose** JWT, **passlib/bcrypt** password hashing, **Jinja2** email templates, **httpx** for outbound calls. Payment gateway is **Flutterwave V4** (OAuth client-credentials; virtual-account + card + transfers). Server-side **Meta Conversions API** events. **SMTP** email.
- **Frontend:** static HTML/CSS/vanilla JS served by FastAPI (`frontend/`), including a large `admin/dashboard.html` and `sales/` pages. Auth tokens live in `sessionStorage`; customer/affiliate access via long-lived tokens in URLs.
- **Structure:** `backend/routes/`, `backend/services/`, `backend/workers/`, `backend/middleware/`, `backend/utils/`, `backend/schemas/`. Four independent APScheduler instances start in `backend/main.py` on startup (email, payout, affiliate-nudge, subscription).
- **Deploy:** production appears to run FastAPI directly (Render-style, behind a reverse proxy). A secondary `deploy/docker-compose.yml` + `deploy/nginx.conf` also exists.

**Known-good behaviors you MUST preserve** (do not "fix" these — they are correct and were hardened deliberately):

- `backend/services/payment_completion.py::complete_payment()` is intentionally **idempotent** via the unique index on `payments.reference` as the atomic claim, with a subscriber/email-queue safety-net that runs regardless of who won the claim. Keep this contract intact.
- The email worker (`backend/workers/email_scheduler.py::process_email_queue`) claims each item atomically with `find_one_and_update` (`status -> "sending"`) and serializes with an `asyncio.Lock`; it has exponential backoff, a startup "rescue stuck sending" job, and an hourly health check. This is safe across processes because of the DB-level claim. Keep it.
- Webhook signature verification in `backend/routes/payments.py::flutterwave_webhook` **fails closed** (rejects if no secret configured, no/invalid signature). Keep fail-closed.
- `resend_library_link` returns a generic response for both existing and non-existing emails (no user enumeration). Keep it generic.
- Emails escape user data with `html.escape()` and Jinja2 autoescape. Keep it.
- The Meta CAPI senders no-op safely when their tokens are blank. Keep that.

---

## GLOBAL RULES (apply to every task)

1. **Work systematically, phase by phase, in the order given.** Do not jump around.
2. **Inspect the actual code before changing it.** Confirm each finding against the real files. If a finding does not match the current code, note the discrepancy and adjust rather than blindly applying the change.
3. **Make changes in small, logical, reviewable groups.** One concern per change set.
4. **Do not do aesthetic rewrites.** Only change what a task requires or what is needed for correctness/security/performance/reliability/maintainability.
5. **Preserve existing working functionality.** The "Constraints" field of each task lists what must not break.
6. **Do not add new dependencies** unless a task explicitly calls for it or it is genuinely unavoidable; prefer the stack already present.
7. **Follow existing conventions:** timezone-aware `datetime.now(timezone.utc)`, the `routes/services/workers` split, Pydantic v2 schemas, the `complete_payment`-style idempotency pattern for money operations.
8. **After every phase, run a regression pass** (see Verification) and confirm no previously-working flow broke.
9. **Test the actual affected user flow end-to-end**, not just the unit. Cover edge cases and failure paths, not only the happy path.
10. **Never mark a task done because code compiles.** Prove the intended behavior works (execution, test, or a clearly-reasoned manual trace when execution isn't possible).
11. **Explain each major decision** briefly in your change notes, especially any deviation from a task's suggested approach.
12. Keep secrets out of code and logs. Do not print tokens, card data, or full webhook auth headers.

---

## PHASE 0 — UNDERSTAND THE CODEBASE (do this before any change)

Instructions:

- Read and map these before editing anything: `backend/main.py`, `backend/config.py`, `backend/database.py`, `backend/middleware/auth.py`, `backend/utils/security.py`, `backend/utils/rate_limit.py`, all `backend/routes/*.py`, all `backend/services/*.py`, all `backend/workers/*.py`, `backend/schemas/schemas.py`, `frontend/js/checkout.js`, `frontend/js/main.js`, `frontend/admin/dashboard.html`, `frontend/sales/*.html`, `deploy/*`, `tests/*`, `.github/workflows/tests.yml`.
- Build a dependency map of the money paths specifically: how `referrals.commission_status` is written (find every writer), how subscriptions are billed and advanced, and how a payout batch is built/approved/sent.
- Identify every place that reads `request.client.host` and every `@limiter.limit(...)` usage.
- Identify every `innerHTML`/template-literal render sink in `frontend/admin/dashboard.html` and which of them interpolate server data derived from user input (`name`, `email`, etc.).
- Confirm how the app is actually run in production (start command, whether behind a proxy) so Phase 5's proxy fix targets the right entrypoint.
- Produce a short written confirmation of which findings below you verified as still-present, and any you found already-fixed or inaccurate. **Do not proceed to Phase 1 until this confirmation exists.**

Constraint: Phase 0 is read-only. Make no code changes.

---

## PHASE 1 — CRITICAL BUGS, MONEY INTEGRITY, BROKEN CORE FLOWS

> These can lose money, compromise the admin, or silently break revenue. Fix first.

### TASK 1.1 — Eliminate the double-payment pathway in affiliate commission settlement
- **Problem:** Two independent subsystems both mark affiliate commissions as paid, so the same commission can be paid twice (once by hand, once automatically) or state can drift mid-batch.
- **Location:** `backend/services/payout_service.py` (`send_batch`, `withdraw_settlement_share`); `backend/routes/admin_payouts.py` (`approve_batch`, `sync_pending_batch`); `backend/routes/affiliates.py` (`mark_commission_paid`, path `/api/admin/affiliates/{affiliate_id}/mark-paid`); `backend/routes/admin.py` (`mark_affiliate_payout`, path `/api/admin/affiliates/{code}/mark-payout`); `backend/services/flutterwave.py` (`create_transfer`). Data: `referrals.commission_status`, `payout_batches`.
- **Root cause:** The program began as "tracking only" (admin pays out-of-band, then flips a status flag). An automated Flutterwave Transfers payout system was added later without retiring the manual flag-flip endpoints. Both mutate `commission_status`. Additionally, `send_batch` generates a **fresh random per-item reference on every approve**, so Flutterwave's reference-idempotency does not prevent a re-approve/double-click from paying twice. `mark_affiliate_payout` also uses `{"commission_status": {"$ne": "paid"}}`, which can flip referrals that a batch is mid-processing.
- **Required change:**
  1. Choose **one** settlement authority. Recommended: the automated payout-batch system is the authority; the manual "mark paid" endpoints become either (a) removed, or (b) reduced to an explicit, clearly-labeled "record an out-of-band manual payment" action that is mutually exclusive with a referral being in an active/sent batch.
  2. Make batch approval **atomic and single-shot**: transition the batch `pending_approval/failed_partial -> sending` with a conditional (compare-and-swap) update and refuse to proceed if the CAS fails, so a double-click / concurrent approve cannot both send.
  3. Give each payout item a **stable, deterministic reference** derived from the batch id + affiliate code (not a fresh `uuid4` each approve), so a retried approve reuses Flutterwave's idempotency instead of creating a new transfer.
  4. Guard the referral state transition so a referral can only move `unpaid -> paid` once, keyed to the specific settlement event that paid it (store `payout_reference`/`batch_id` on the referral).
- **Expected behaviour:** A commission can be settled exactly once. Re-approving a batch, double-clicking approve, or concurrent admins cannot pay an affiliate twice. Manual and automated settlement cannot both claim the same referral.
- **Constraints:** Do not change how commission *amount* is locked in at conversion time (`payment_completion.py`). Do not break the "failed items roll into the next batch" behavior. Partial-failure batches must still be resumable.
- **Verification:** Simulate: build a batch, approve it twice in quick succession, and confirm exactly one transfer intent per item and each referral flips to paid once. Simulate a manual mark-paid on a referral already in a sent batch and confirm it cannot double-settle. Add/extend automated tests around `send_batch` idempotency.

### TASK 1.2 — Make recurring subscription billing idempotent (stop double-charges)
- **Problem:** The daily subscription billing job can charge a customer's card twice.
- **Location:** `backend/workers/subscription_scheduler.py::run_daily_subscription_billing` (and `handle_billing_failure`). Data: `subscriptions`, `subscription_billing_logs`.
- **Root cause:** The job selects `status:"active", next_charge_date <= now`, charges via `charge_token`, then updates `next_charge_date` — with **no atomic claim of the billing period** before charging, and a **random** reference (`SUB-REN-{id}-{hex}`) so Flutterwave sees a new idempotency key each attempt. Two overlapping runs (or a crash between charge success and the `next_charge_date` update) re-charge the same period.
- **Required change:** Before charging, **atomically claim the current billing period** (e.g., conditionally advance `next_charge_date` / set a `billing_in_progress` marker keyed to the period via a single `find_one_and_update`, so only one runner can claim a given due charge). Use a **deterministic idempotency key/reference** derived from subscription id + the billing period being charged, so a retry of the same period cannot create a second charge. On success, finalize; on failure, run the existing past-due fallback and release/roll the claim correctly.
- **Expected behaviour:** Each subscription is charged at most once per billing period, even under overlapping scheduler runs or a mid-run crash.
- **Constraints:** Preserve the past-due fallback (manual checkout link email) and the success email. Do not alter the 30-day cadence or the mock-token dev path (`APP_ENV == "development"`).
- **Verification:** Simulate two concurrent invocations against the same due subscription and confirm exactly one charge. Simulate charge-success-then-crash-before-update and confirm the next run does not re-charge. Confirm past-due path still fires on decline.

### TASK 1.3 — Fix stored XSS in the admin dashboard
- **Problem:** Attacker-controlled text (customer/lead/affiliate `name`, and any free-text field) executes as script in the admin's authenticated browser.
- **Location:** `frontend/admin/dashboard.html` — render sites using `innerHTML` / template literals with raw `${...}`, including recent-sales, recent-leads, customers table, transaction/customer drawers, affiliates table (approx. lines 948, 966, 973, 1050, 1085–1086, 1200–1206, 1228–1229, 1300–1301), and `ai_insights` mapped as raw HTML (~948). Also verify `frontend/sales/dashboard.html`.
- **Root cause:** `name` is validated only for length in `backend/schemas/schemas.py`; it is rendered without HTML-escaping into `innerHTML`.
- **Required change:** Escape all user-derived strings at every HTML render sink (introduce and use a small `escapeHtml` helper for all interpolated dynamic values, or switch those sinks to `textContent`/DOM node creation). Cover table cells, drawers, CSV/inline attributes, and the `onclick="...('${...}')"` sinks (these need JS-string-safe encoding too). Escape `ai_insights` items even though currently empty.
- **Expected behaviour:** A customer named `<img src=x onerror=alert(1)>` renders as inert text in every admin view; no script executes.
- **Constraints:** Do not change what data the admin sees, only how it is rendered. Keep table layouts, click handlers, and drawer behavior intact.
- **Verification:** Create a record with a script-payload name via the real API, load each affected admin view, confirm no execution and correct literal display. Check the transaction drawer, customer profile drawer, affiliates table, and CSV export path.

### TASK 1.4 — Fix (or explicitly disable) the live sales-rep card checkout
- **Problem:** Real (non-mock) sales-rep card charges likely fail at the gateway; the subscription-sales revenue path may be silently broken in production.
- **Location:** `backend/routes/sales.py::process_checkout_payment`.
- **Root cause:** The charge payload sends `"customer_id": lead["prospect_email"]` — an email where Flutterwave expects a real customer id. Everywhere else the code first calls `create_flw_customer(...)` to obtain a valid id. Only the `mock-payment-method-id` dev path is exercised by tests, so the bug is invisible. Errors surface as a bare `Exception` → opaque 500.
- **Required change:** Before creating the charge, create/resolve a Flutterwave customer for the prospect (reuse `create_flw_customer`) and pass the returned `customer_id`. Replace the bare `raise Exception(...)` with a mapped `HTTPException` and gateway-error handling consistent with `routes/payments.py`. If for any reason this channel is intended to be dormant, instead gate it behind an explicit config flag and return a clear "unavailable" response rather than a broken charge.
- **Expected behaviour:** A real card checkout for a sales lead either completes against Flutterwave with a valid customer id, or fails with a clear, handled error — never a silent 500 from an invalid payload.
- **Constraints:** Preserve the `mock-payment-method-id` + `APP_ENV=="development"` simulation path and the `pending_subscription_payments`/`subscriptions`/`one_time_purchases` record shapes. Preserve `verify_checkout_payment`'s success/decline handling.
- **Verification:** Exercise the mock path (still works) and trace the real path with a sandbox card to confirm a valid `customer_id` is sent and a charge is created; confirm errors return handled HTTP responses.

---

## PHASE 2 — DATA, BACKEND, API, CONCURRENCY, VALIDATION

### TASK 2.1 — Prevent duplicate scheduler execution across processes/instances
- **Problem:** All four APScheduler instances run in-process with no leader election; scaling beyond one instance/worker duplicates subscription billing and payout builds.
- **Location:** `backend/main.py` startup; `backend/workers/email_scheduler.py`, `payout_scheduler.py`, `affiliate_nudge_scheduler.py`, `subscription_scheduler.py`.
- **Root cause:** Implicit "exactly one process forever" assumption. Email is protected by DB-level atomic claims; billing and payout-build are not.
- **Required change:** Introduce a single-leader guard for the schedulers (e.g., a MongoDB-backed advisory lock / lease document that only one instance holds, or run schedulers only when an explicit `RUN_SCHEDULERS`/leader env flag is set). Ensure billing and payout jobs additionally rely on the per-period/per-day atomic guards from Tasks 1.1/1.2 as defense-in-depth. Document the chosen scaling model in-code.
- **Expected behaviour:** With N app instances, each scheduled job runs once per interval globally.
- **Constraints:** Single-instance deployments must keep working with no config change (safe default). Do not weaken the email worker's existing atomic-claim safety.
- **Verification:** Start two app processes against one DB; confirm one billing run, one payout-build per period. Confirm single-instance still schedules normally.

### TASK 2.2 — Restore true client IP behind the proxy
- **Problem:** Per-IP rate limits and IP logging are defeated; all requests appear to come from the proxy.
- **Location:** `backend/utils/rate_limit.py` (`get_remote_address`), all `@limiter.limit(...)` routes, IP reads in `routes/payments.py`, `routes/affiliate_public.py`, `routes/tracking.py`, `routes/community.py`, `routes/main.py` webhook log; app start in `backend/main.py`; `deploy/nginx.conf` (sets `X-Forwarded-For`).
- **Root cause:** App reads `request.client.host` (socket peer = proxy) and is not configured to trust forwarded headers (no `--proxy-headers` / `ProxyHeadersMiddleware` / trusted-hosts).
- **Required change:** Configure the app to derive the real client IP from the proxy's forwarded header **only when behind a trusted proxy** (enable Uvicorn `--proxy-headers` with an appropriate `forwarded-allow-ips`, or add the equivalent middleware), and make the rate-limiter key function use that real IP. Keep it safe: do not trust `X-Forwarded-For` from arbitrary clients when not behind a proxy.
- **Expected behaviour:** Rate limits bucket per real end-user IP; login/checkout/registration abuse controls and the per-IP affiliate-signup cap function; stored IPs are the real client IPs.
- **Constraints:** Do not open header spoofing when running locally/without a proxy. Keep existing limit thresholds unless a task says otherwise.
- **Verification:** Behind the proxy, confirm two different clients get independent limit buckets and logged IPs differ; confirm a client cannot spoof its IP when the proxy is not trusted.

### TASK 2.3 — Reconcile/align the duplicate "mark paid" endpoints
- **Problem:** Two overlapping admin endpoints settle commissions with different keys and semantics (code vs id), confusing and error-prone even after Task 1.1.
- **Location:** `backend/routes/admin.py` (`/api/admin/affiliates/{code}/mark-payout`) and `backend/routes/affiliates.py` (`/api/admin/affiliates/{affiliate_id}/mark-paid`).
- **Root cause:** Feature added twice during evolution.
- **Required change:** Consolidate to one endpoint/semantics consistent with the settlement authority chosen in Task 1.1; remove or clearly deprecate the other; update the admin frontend caller accordingly.
- **Expected behaviour:** One well-defined way to record/settle commission, matching Task 1.1.
- **Constraints:** Update `frontend/admin/dashboard.html` calls so no button 404s. Do not orphan UI.
- **Verification:** Exercise the surviving endpoint from the dashboard; confirm the removed one is no longer referenced.

### TASK 2.4 — Enforce upload size and content validation
- **Problem:** `MAX_FILE_SIZE_MB` is configured but never enforced; only the `.pdf` filename suffix is checked.
- **Location:** `backend/routes/admin.py::upload_product`; `backend/config.py` (`MAX_FILE_SIZE_MB`).
- **Root cause:** Validation was never wired to the config; content-type/size not checked.
- **Required change:** Enforce the configured max size during the streamed write (reject oversize), and validate content type (PDF) beyond the filename. Keep the existing safe-name sanitization and threadpool write.
- **Expected behaviour:** Oversize or non-PDF uploads are rejected with a clear 400; valid uploads behave as before.
- **Constraints:** Admin-only endpoint; do not block legitimate PDFs. Preserve `run_in_threadpool` non-blocking write.
- **Verification:** Upload an oversize file and a non-PDF; confirm rejection. Upload a normal PDF; confirm it still saves and lists.

### TASK 2.5 — Replace bare exceptions with mapped HTTP errors in request handlers
- **Problem:** Some endpoints raise bare `Exception`, producing opaque 500s.
- **Location:** `backend/routes/sales.py` (`process_checkout_payment` gateway error) and any similar handler-level `raise Exception(...)`.
- **Root cause:** Inconsistent error handling.
- **Required change:** Convert handler-level bare exceptions into appropriate `HTTPException`s (e.g., 502 for gateway failures) consistent with `routes/payments.py`. Keep internal service-layer exceptions as-is where they are caught and translated by callers.
- **Expected behaviour:** Predictable, mapped HTTP status codes; no accidental stack-trace 500s on known failure modes.
- **Constraints:** Do not swallow real errors silently; still log server-side.
- **Verification:** Force a gateway error and confirm a clean 5xx with a user-safe message.

### TASK 2.6 — Normalize datetime handling
- **Problem:** Mixed naive/aware datetimes risk `TypeError` on comparison during future edits.
- **Location:** `backend/services/affiliate_health_service.py` (uses naive `datetime.utcnow()` deliberately) vs. the timezone-aware convention everywhere else.
- **Root cause:** Motor returns naive datetimes for some stored fields; the service matched that with naive comparisons.
- **Required change:** Make the datetime strategy explicit and consistent (prefer timezone-aware `datetime.now(timezone.utc)` and normalize values read back before comparison), or clearly encapsulate the naive-comparison rationale so a future refactor can't silently break it.
- **Expected behaviour:** No naive-vs-aware comparison hazards; health metrics unchanged.
- **Constraints:** Do not change the computed metric values/outputs.
- **Verification:** Run the affiliate-health computation over seeded data spanning month boundaries; confirm identical outputs and no comparison errors.

---

## PHASE 3 — PERFORMANCE

### TASK 3.1 — Remove unbounded in-memory collection scans
- **Problem:** Full-collection `to_list(100000)` loads scale linearly in memory/latency on admin page loads.
- **Location:** `backend/routes/admin.py::get_analytics_customers` (`db.users.find(...).to_list(100000)` then `$in` over all emails) and `get_sequence_overview` (`db.subscribers.find(...).to_list(100000)`).
- **Root cause:** Global metrics computed by pulling every document into the app.
- **Required change:** Compute the global aggregates with server-side aggregation pipelines and paginate the row lists; avoid materializing entire collections in Python.
- **Expected behaviour:** Same numbers and same paginated rows, computed without loading the whole collection.
- **Constraints:** Preserve the returned metric semantics (repeat-purchase rate, avg CLV, stage distribution, subscribers-behind counts, pagination shape).
- **Verification:** Compare outputs against the current implementation on a seeded dataset (identical results); confirm memory/query profile improved.

### TASK 3.2 — Batch the N+1 offer lookups
- **Problem:** `offers.find_one` is called once per subscription in loops.
- **Location:** `backend/routes/admin.py` (`admin_get_subscriptions`, `admin_get_subscriptions_kpis`); `backend/workers/subscription_scheduler.py` (per-sub offer fetch).
- **Root cause:** Per-row lookups instead of a single batched query.
- **Required change:** Fetch the needed offers once via `$in` and map by id. (In the billing worker, still fetch offers efficiently before the charge loop.)
- **Expected behaviour:** Identical resolved offer names/prices with far fewer DB round trips.
- **Constraints:** Do not change MRR/KPI math or subscription records.
- **Verification:** Compare admin subscriptions/KPIs output before/after on seeded data; confirm identical values and fewer queries.

### TASK 3.3 — Lightly cache hot public counters and avoid redundant recompute
- **Problem:** `/api/public/sales-count` recomputes a `count_documents` on every visitor poll (every 30s); `sync_pending_batch` rewrites the batch doc even on read; `list_sales_reps` runs 2 counts per rep.
- **Location:** `backend/main.py::get_public_sales_count`; `backend/routes/admin_payouts.py::sync_pending_batch` (called from list/get); `backend/routes/admin.py::list_sales_reps`.
- **Root cause:** No short-TTL caching / read-path does write work / per-row counts.
- **Required change:** Add a small short-TTL cache (or equivalent) to the public sales count; make `sync_pending_batch` avoid unnecessary writes when nothing changed on pure reads; batch the sales-rep counts with aggregation.
- **Expected behaviour:** Same displayed values; fewer DB operations on hot paths.
- **Constraints:** The public counter's "only show at 500+" frontend logic and the batch figures must remain correct and reasonably fresh.
- **Verification:** Confirm counts still update within an acceptable window; confirm no functional change to batch figures or rep counts.

> Do not micro-optimize beyond these. Preserve correctness over cleverness.

---

## PHASE 4 — FRONTEND & USER EXPERIENCE

### TASK 4.1 — Confirm and fix admin/sales dashboard behavior after XSS-escaping (Task 1.3)
- **Problem:** Escaping changes must not break click handlers, drawers, CSV export, or inline `onclick` args.
- **Location:** `frontend/admin/dashboard.html`, `frontend/sales/dashboard.html`.
- **Root cause:** Same render sinks are reused for display and for JS-string interpolation in `onclick`.
- **Required change:** Ensure escaping is context-correct (HTML-escape for text nodes, JS-string-safe for `onclick` args, attribute-safe for attributes). Prefer event listeners + `dataset` over inline `onclick` with interpolated values where practical.
- **Expected behaviour:** All tables, filters, profile/transaction drawers, and CSV export work exactly as before, now safe.
- **Constraints:** No visual/behavioral regression to the dashboards.
- **Verification:** Click through every table row, drawer, resend/refund/mark-paid button, and CSV export with a payload-name record present.

### TASK 4.2 — Verify checkout resume, polling, and success flows still behave
- **Problem:** Any backend change to `/api/payments/verify` shape or IP handling must not break the frontend polling/resume logic.
- **Location:** `frontend/js/checkout.js` (poll loop, `resumePendingPaymentOnLoad`, `fireVerifiedPurchase`), `frontend/js/main.js` (countdown/price, live counter).
- **Root cause:** Frontend depends on `verify` returning `{success, token, magic_link, amount}` and on storage-failure isolation.
- **Required change:** No functional change unless a backend task altered the `verify` contract; if so, keep the response shape stable. Confirm the storage-blocked (in-app browser) path still redirects via URL token.
- **Expected behaviour:** Transfer → poll → success → `/welcome?token=...`; tab-close → resume banner or silent completion; Pixel fires once per reference.
- **Constraints:** Keep the `verify` response contract stable; keep the per-reference localStorage dedup guard.
- **Verification:** End-to-end: simulate a successful verify (mock), confirm redirect, single Pixel fire, and the resume-on-load path both when success and when still-pending.

### TASK 4.3 — Address token-in-URL UX/security for library & affiliate dashboards (coordinate with Task 5.2)
- **Problem:** Long-lived tokens in URLs are a UX/security liability (history/Referer leakage; affiliate token can change payout bank).
- **Location:** `frontend/library.html`, `frontend/affiliate-dashboard.html`, and backend token issuance/validation (`routes/library.py`, `routes/affiliate_dashboard.py`).
- **Root cause:** Permanent bearer secret in query string.
- **Required change:** Implement the backend token lifetime/rotation from Task 5.2; on the frontend, avoid leaving the raw token in the address bar longer than necessary (e.g., store then clean the URL) and ensure re-auth/expiry is handled gracefully with a clear "link expired, request a new one" flow.
- **Expected behaviour:** Access still works from an emailed link, but a stale/expired token prompts a safe re-request rather than silently granting forever.
- **Constraints:** Do not lock out legitimate customers/affiliates; keep the email-link entry point working.
- **Verification:** Open a fresh link (works), an expired link (clean re-request flow), and confirm the token isn't needlessly persisted in browser history.

---

## PHASE 5 — SECURITY & RELIABILITY

### TASK 5.1 — Harden the deploy configuration
- **Problem:** Unauthenticated MongoDB and broad port exposure in compose; nginx doesn't route FastAPI page/redirect endpoints.
- **Location:** `deploy/docker-compose.yml` (Mongo with no auth, `27017:27017`, backend `8000:8000` public), `deploy/nginx.conf` (only `/api/` proxied; `/r/{code}`, `/sales/*`, `/affiliate/*`, `/unsubscribe` not routed).
- **Root cause:** Compose/nginx are a secondary/stale deployment path that diverged from how FastAPI actually serves routes.
- **Required change:** Add MongoDB authentication and stop publishing the DB port publicly; restrict backend exposure to the proxy network. Update `nginx.conf` to proxy all non-static FastAPI routes (or document clearly that FastAPI is the sole front door and align the compose accordingly). Ensure the chosen topology actually serves affiliate referral links and page routes.
- **Expected behaviour:** In the Docker topology, all routes work and the database is not internet-reachable without credentials.
- **Constraints:** Do not break the production (direct-FastAPI) deployment. Keep `uploads/` protected (nginx already denies direct access).
- **Verification:** Bring up the compose stack; hit `/`, `/r/{code}`, `/sales/checkout`, `/affiliate/dashboard`, `/api/health`; confirm all resolve and Mongo requires auth.

### TASK 5.2 — Add lifetime/rotation to library & affiliate access tokens
- **Problem:** `library_access_token` and `dashboard_token` never expire; the affiliate token authorizes bank-detail changes.
- **Location:** `backend/utils/security.py`, `backend/services/payment_completion.py` (issuance), `backend/routes/library.py`, `backend/routes/affiliate_dashboard.py` (validation + `POST /bank-details`).
- **Root cause:** Permanent bearer secrets with no expiry/rotation and a sensitive write behind one of them.
- **Required change:** Introduce token expiry and/or rotation (e.g., time-bounded tokens with a self-service "resend link" refresh, which already exists for library). For the **affiliate bank-detail change specifically**, add a stronger step (short-lived confirmation token or re-verification) so a leaked long-lived dashboard token alone cannot silently reroute payouts.
- **Expected behaviour:** Access links work from email; sensitive payout-bank changes require a fresh confirmation; stale tokens fail safely with a re-request path.
- **Constraints:** Keep the existing `resend-link` recovery and generic-response anti-enumeration behavior. Don't lock out legitimate users.
- **Verification:** Confirm a fresh link works, an old one is rejected, resend recovers access, and a bank-detail change requires the added confirmation step.

### TASK 5.3 — Constant-time admin credential comparison & stronger password policy
- **Problem:** Env-admin password compared with `==` (timing side-channel); weak min length; startup check only catches the shipped default.
- **Location:** `backend/routes/admin.py::admin_login`; `backend/schemas/schemas.py` (`AdminLoginRequest`, sales password fields); `backend/main.py::check_admin_password_rotated`.
- **Root cause:** Direct string compare; permissive validation.
- **Required change:** Use `secrets.compare_digest` for the env-admin compare. Raise minimum password length for admin/sales credential creation to a sane policy. Optionally extend the startup check to warn on obviously-weak custom values (not just the default).
- **Expected behaviour:** No trivial timing leak; new credentials meet a stronger minimum.
- **Constraints:** Don't lock out the existing admin; keep the DB-admin bcrypt path unchanged. Don't hard-fail production on already-set reasonable passwords.
- **Verification:** Login still works with correct creds; weak new passwords are rejected at creation.

### TASK 5.4 — Fix the misleading download-link comment and confirm behavior
- **Problem:** A code comment claims the signed download link "has no separate time-based expiry … remains valid indefinitely," but the token actually expires (`exp = now + JWT_DOWNLOAD_EXPIRE_MINUTES`).
- **Location:** `backend/routes/library.py::download_file` comment vs. `backend/utils/security.py::create_download_token`.
- **Root cause:** Comment drifted from behavior after the single-use gate was removed.
- **Required change:** Correct the comment to reflect the real behavior (time-bounded, reusable within the window). Confirm `verify_token` enforces `exp`. Decide consciously whether the 10-minute reusable window is the intended policy; if a stricter policy is wanted, note it but do not implement single-use (it was deliberately removed to avoid locking out flaky-mobile retries).
- **Expected behaviour:** Documentation matches behavior; download links expire per config and remain reusable within that window.
- **Constraints:** Do not re-introduce the single-use gate that caused false lockouts.
- **Verification:** Confirm a link works within the window, fails after expiry, and a legitimate retry within the window still succeeds.

### TASK 5.5 — Secrets hygiene
- **Problem:** A `.env` with real-looking live credentials (Atlas URI w/ password, SMTP password, Flutterwave secret) sits in the working tree and is loaded by tests if present.
- **Location:** project root `.env` (git-ignored, not tracked — confirm this stays true), `tests/conftest.py` (`_load_dotenv_into_environ`).
- **Root cause:** Operational convenience file in the repo folder.
- **Required change:** Confirm `.env` remains git-ignored and untracked; ensure it is never copied into any built image (Dockerfile already excludes it — verify). Recommend rotating any credential that may have been exposed if the folder was ever shared. Ensure CI uses only injected test env, not the real `.env`.
- **Expected behaviour:** No real secret is committed, imaged, or logged; tests run on injected/ephemeral values.
- **Constraints:** Don't break local dev that relies on `.env`; don't print secret values anywhere.
- **Verification:** `git ls-files` shows no `.env`; a built image contains no `.env`; CI passes using only workflow-provided env.

### TASK 5.6 — Reconsider fabricated social-proof fallback (conscious decision, not a silent bug)
- **Problem:** `/api/public/sales-count` returns a hardcoded `38` when the DB is unavailable — a fabricated number shown as "live."
- **Location:** `backend/main.py::get_public_sales_count`.
- **Root cause:** Fallback to keep the counter populated when DB is down.
- **Required change:** Make this an explicit, intentional decision: either remove the fabricated fallback (return a neutral state and let the frontend hide the counter) or keep it with an in-code note that it is deliberate. Do not leave it ambiguous.
- **Expected behaviour:** The "live" counter is either genuinely live or cleanly hidden — no unexplained fabricated figure.
- **Constraints:** The frontend already hides the counter below 500; keep that logic coherent.
- **Verification:** With DB down, confirm the counter behaves per the chosen policy.

---

## PHASE 6 — ARCHITECTURE & MAINTAINABILITY (only where it buys correctness/clarity)

### TASK 6.1 — Single-source the 52-email sequence metadata
- **Problem:** Email subjects exist twice — `backend/workers/email_scheduler.py::EMAIL_SEQUENCE` and a hardcoded `_SEQ_SUBJECTS`/`_SEQ_DAY_OFFSETS` in `backend/routes/admin.py`. They can drift.
- **Location:** the two lists above.
- **Root cause:** Copy for the admin sequence-monitor view.
- **Required change:** Derive the admin monitor's subjects/offsets from the single canonical `EMAIL_SEQUENCE` (import/expose it) instead of a duplicated literal list.
- **Expected behaviour:** One source of truth; admin monitor always matches what's actually queued.
- **Constraints:** Keep the monitor's output identical for the current sequence.
- **Verification:** Confirm the sequence-overview and per-subscriber views show the same subjects/offsets as before, now sourced canonically.

### TASK 6.2 — Resolve the dead analytics router
- **Problem:** `backend/routes/admin_analytics.py` (~600 lines) is intentionally not wired up and duplicates logic now living in `routes/admin.py`.
- **Location:** `backend/routes/admin_analytics.py`, `backend/main.py` (commented-out include).
- **Root cause:** Left dormant "pending a decision."
- **Required change:** Make the decision: remove the dead file (preferred, since its logic is superseded), or adopt it and delete the duplicate in `admin.py`. Do not keep both.
- **Expected behaviour:** No dead, drift-prone duplicate router remains.
- **Constraints:** Whichever is kept must serve the exact endpoints the admin frontend calls; verify no dashboard tab 404s.
- **Verification:** Load every admin dashboard tab; confirm all data endpoints resolve.

### TASK 6.3 — De-duplicate the `TokenResponse` schema
- **Problem:** `TokenResponse` is defined in both `backend/schemas/schemas.py` and inline in `backend/routes/sales.py`.
- **Location:** those two files.
- **Root cause:** Local redefinition.
- **Required change:** Use the shared schema in `sales.py`; remove the duplicate.
- **Expected behaviour:** One definition; identical response shape.
- **Constraints:** Response payloads unchanged.
- **Verification:** Sales login/response unchanged; import resolves.

> Do NOT undertake broad refactors of `admin.py` or `dashboard.html` file size purely for aesthetics. Splitting giant files is optional and only acceptable if it does not risk regressions; if attempted, do it as an isolated, separately-verified change after all functional fixes land.

---

## THINGS TO EXPLICITLY LEAVE UNCHANGED (do not "fix" these)

- The idempotent `complete_payment()` claim-and-safety-net design.
- The email worker's atomic `find_one_and_update` claim, `asyncio.Lock`, exponential backoff, startup rescue, and hourly health check.
- Webhook fail-closed signature verification.
- Generic anti-enumeration response in `resend_library_link`.
- Persistent SMTP connection reuse with NOOP re-validation in `email_service.py`.
- The removal of the single-use download gate (kept off intentionally to avoid mobile-retry lockouts) — only fix the comment (Task 5.4).
- Affiliate referral links intentionally charging the late price (₦5,000) — business rule, not a bug.
- The mock payment/dev bypass paths gated by `APP_ENV == "development"` — keep them working for tests.

---

## VERIFICATION REQUIREMENTS (run after each phase and at the end)

1. **Builds & imports:** `python -m py_compile` across `backend/` passes; app imports cleanly.
2. **App starts:** FastAPI starts, connects to Mongo (or logs the UI-only fallback), schedulers start under the leader-guard, `/api/health` returns ok.
3. **Existing tests pass:** run the suite (`pytest -v`) using the CI-style ephemeral Mongo + injected env; keep all current tests green. Add tests where noted below.
4. **Money paths (execution-verified):**
   - Payout batch: build → approve twice → exactly one transfer intent per item, each referral paid once.
   - Subscription billing: two concurrent runs on one due sub → one charge; crash-after-charge → no re-charge next run; decline → past-due fallback.
5. **Security:**
   - Stored-XSS: payload-name record renders inert across all admin/sales views.
   - Rate limiting: distinct client IPs get distinct buckets behind the proxy; no IP spoofing when proxy untrusted.
   - Tokens: expired library/affiliate links fail safely; bank-detail change requires the added confirmation.
   - No secrets tracked/imaged/logged.
6. **Core flows end-to-end:** landing → checkout (virtual account + card/redirect) → verify → `/welcome` → `/library` download; affiliate register → referral click `/r/CODE` → attributed conversion → dashboard stats; sales lead → checkout (mock and real-path traced) → subscription/one-time record; unsubscribe link.
7. **Performance:** admin customers/sequence endpoints return identical values without full-collection loads; subscription/KPI endpoints return identical values with batched offer lookups; public counter cached.
8. **Regression sweep:** every admin dashboard tab loads with no 404; all dashboard buttons (resend, refund, mark-paid, toggle status, create rep) work; checkout resume-on-load works in both success and pending states.
9. **Edge cases, not just happy path:** DB-down UI-only mode, blank Flutterwave/Meta tokens (no-op), storage-blocked in-app browser checkout, expired tokens, oversize/non-PDF upload, orphaned referral (deleted affiliate) in payout build.
10. **No new dependencies** beyond what a task justified; note any that were unavoidable.

Where execution isn't possible for a given item, provide a clear, code-referenced trace proving the intended behavior — but prefer real execution.

## COMPLETION CRITERIA

A task is complete only when its **Expected Behaviour** is demonstrated (execution or rigorous trace), its **Constraints** are shown intact, and its **Verification** steps pass. The overall job is complete only when every task above is either implemented-and-verified or explicitly documented as intentionally-not-changed with a reason, and the full Verification Requirements list passes with no known regressions.

---

# PART 2 — RECOMMENDED IMPLEMENTATION ORDER

1. **Phase 0** — inspect, map money paths and render sinks, confirm each finding against real code, confirm the production run command. (No changes.)
2. **Phase 1 (money & trust first):** 1.1 commission double-pay → 1.2 subscription double-charge → 1.3 admin stored XSS → 1.4 sales card checkout. Regression sweep.
3. **Phase 2 (backend correctness/concurrency):** 2.1 scheduler leader-guard → 2.2 real client IP → 2.3 consolidate mark-paid → 2.4 upload limits → 2.5 mapped errors → 2.6 datetimes. Regression sweep.
4. **Phase 5 (security/reliability)** next, because several items pair with Phase 1/2: 5.2 token lifetime (pairs with 4.3), 5.1 deploy hardening, 5.3 admin creds, 5.4 comment fix, 5.5 secrets, 5.6 social-proof decision. Regression sweep.
5. **Phase 3 (performance):** 3.1 unbounded scans → 3.2 N+1 offers → 3.3 caching. Verify identical outputs.
6. **Phase 4 (frontend/UX):** 4.1 dashboard behavior post-escaping → 4.2 checkout flow verification → 4.3 token-in-URL UX. Full end-to-end sweep.
7. **Phase 6 (maintainability):** 6.1 single-source sequence → 6.2 dead router → 6.3 duplicate schema. Optional file-splitting only if risk-free.
8. **Final full verification** per the Definition of Done.

Rationale: fix the highest-consequence, hardest-to-see money/security defects before touching performance or cosmetics, and land each backend change before the frontend work that depends on its contract.

---

# PART 3 — DEFINITION OF DONE (final checklist)

**Build & run**
- [ ] `python -m py_compile` across `backend/` passes; app imports with no errors.
- [ ] App starts; Mongo connects (or clean UI-only fallback); `/api/health` returns ok.
- [ ] Schedulers run exactly once globally under the leader-guard; single-instance still works with default config.

**Critical money & security (Phase 1/2/5)**
- [ ] A commission cannot be settled twice (manual vs automated reconciled; batch approve is atomic; per-item references are deterministic).
- [ ] A subscription cannot be charged twice per period (atomic period claim + deterministic idempotency key); past-due fallback intact.
- [ ] Stored XSS closed: script-payload names render inert in every admin/sales view, drawer, CSV, and inline handler.
- [ ] Real sales-rep card checkout sends a valid Flutterwave `customer_id` (or is explicitly, cleanly disabled); no opaque 500s.
- [ ] Rate limiting and IP logging use the real client IP behind the proxy; no spoofing when proxy untrusted.
- [ ] Library/affiliate tokens expire/rotate; affiliate bank-detail change needs a fresh confirmation; recovery + anti-enumeration preserved.
- [ ] Deploy hardened: Mongo authenticated and not publicly exposed; nginx routes all FastAPI endpoints (or topology documented and consistent).
- [ ] Admin credential compare is constant-time; password policy strengthened; no secrets tracked/imaged/logged.

**Correctness & data**
- [ ] Duplicate "mark paid" endpoints consolidated; admin UI updated (no 404s).
- [ ] Upload size + content type enforced.
- [ ] Handler-level bare exceptions mapped to proper HTTP errors.
- [ ] Datetime handling consistent; affiliate-health outputs unchanged.
- [ ] Download-link comment corrected to match real (time-bounded, reusable) behavior; single-use gate NOT reintroduced.
- [ ] Social-proof fallback decision made explicit.

**Performance (behavior-preserving)**
- [ ] No unbounded full-collection loads in admin analytics/sequence endpoints; identical outputs.
- [ ] Offer lookups batched; MRR/KPI values identical.
- [ ] Public sales-count cached; batch figures still correct and fresh.

**Frontend / UX**
- [ ] Every admin dashboard tab loads; all buttons (resend/refund/mark-paid/toggle/create rep) work.
- [ ] Checkout: transfer → poll → success → `/welcome`; resume-on-load works in success and pending states; Pixel fires once per reference; storage-blocked path still redirects via URL token.
- [ ] Library/affiliate links: fresh works, expired shows a clean re-request flow.

**Maintainability**
- [ ] Email-sequence metadata single-sourced.
- [ ] Dead analytics router removed or adopted (not both); all admin endpoints resolve.
- [ ] `TokenResponse` de-duplicated.

**Process & regression**
- [ ] `pytest -v` green (existing + added tests for payout idempotency, billing idempotency, XSS-escaping, proxy IP).
- [ ] Core user flows verified end-to-end via execution (or rigorous code-referenced trace where execution is impossible).
- [ ] Edge/failure cases verified (DB-down, blank gateway/Meta tokens, expired tokens, oversize/non-PDF upload, orphaned referral).
- [ ] No new dependencies except those explicitly justified.
- [ ] Every "leave unchanged" item confirmed intact.
- [ ] No known regressions; each major decision documented in change notes.
