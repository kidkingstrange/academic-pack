# Codebase Diagnostic Report — Academic Comeback API

**Scope:** Full read-only technical audit of the entire project (FastAPI backend, static frontend, workers/services, deploy config, tests).
**Method:** File-by-file inspection and cross-referencing. No code was modified, created, or deleted.
**Nature of deliverable:** Findings only. A follow-on engineer/agent should implement the fixes; this report deliberately stops at a high-level remediation roadmap.

---

## 1. Executive Summary

This is a solo-operator, Nigeria-focused digital-product funnel: a landing page sells a ₦2,000/₦5,000 "Academic Comeback Package," collects payment through Flutterwave V4 (virtual account + card), enrolls buyers into a 52-email drip curriculum, and layers on an affiliate program, a sales-rep subscription channel, and an admin dashboard. The core purchase-and-deliver path is, on the whole, **thoughtfully engineered** — the payment-completion flow is genuinely idempotent, the email queue uses atomic DB claims plus backoff, and many past incidents (a 40-hour SMTP outage, double-sends, webhook signature gaps) have been diagnosed and hardened, with the reasoning left in-code as comments.

However, the project has grown well past its original "tracking-only" intent, and the newer subsystems — **automated affiliate payouts**, **recurring subscription billing**, and **admin dashboard rendering** — introduce **real financial and security risk** that the mature parts of the codebase do not. The most serious issues are: (a) **two independent subsystems that both mutate commission payment state**, creating a double-pay pathway; (b) **recurring subscription billing with no idempotency/claim guard**, creating a double-charge pathway; (c) **stored XSS** against the admin via unescaped customer-supplied names; and (d) **per-IP rate limiting and abuse controls that are silently defeated** because the app never reads the proxy's forwarded client IP.

None of these are visible as crashes or failing tests — they are latent, triggered by concurrency, scale, or a malicious actor. That is precisely why they warrant a formal report before further production use.

## 2. Overall Health Score: **68 / 100**

| Dimension | Score | One-line justification |
|---|---|---|
| Architecture | 70 | Clean module layout and shared service paths, but overlapping/duplicated subsystems and 4 in-process schedulers with no leader election. |
| Bugs / Correctness | 62 | Real double-charge / double-pay pathways; a broken real-card sales checkout; contradictory in-code documentation. |
| Performance | 72 | Good indexing and bulk-query discipline in most places; a few unbounded `to_list(100000)` in-memory scans and N+1 loops. |
| Security | 55 | Stored XSS, ineffective rate limiting behind proxy, permanent bearer tokens in URLs, unauthenticated Mongo in compose. |
| Reliability | 70 | Strong email retry/rescue design; weaker for billing/payouts; single-process scheduler assumption. |
| Code Quality | 74 | Readable, well-commented; some giant files and duplicated logic. |
| Testing | 66 | Meaningful, well-targeted regression tests, but thin coverage of the money paths (payouts, subscription billing). |

## 3. Architecture Assessment

The backend follows a sensible FastAPI layout: `routes/` (HTTP), `services/` (business logic), `workers/` (schedulers), `middleware/`, `utils/`, `schemas/`. Payment completion is correctly centralized in a single idempotent `complete_payment()` that every confirmation path (webhook, poll, redirect) funnels through — this is the strongest architectural decision in the project.

The main architectural problems are **feature-layer overlap accumulated over time**:

- **Two commission-payment subsystems coexist.** `routes/affiliates.py` documents the affiliate program as *"a tracking system, not a payments system… No Transfers API, no automated transfer,"* yet `services/payout_service.py` + `routes/admin_payouts.py` + `services/flutterwave.create_transfer()` **do** move real money automatically. Both mutate `referrals.commission_status = "paid"`. Additionally there are **two different "mark paid" endpoints** (`admin.py` `/affiliates/{code}/mark-payout` keyed by code, and `affiliates.py` `/affiliates/{affiliate_id}/mark-paid` keyed by id) with subtly different queries. This is a design contradiction, not just duplication (see Finding H-1).
- **A whole dormant router.** `backend/routes/admin_analytics.py` (600 lines) is intentionally not wired into `main.py`; its logic was re-implemented inside `routes/admin.py`. It is dead architecture kept "pending a decision."
- **Four independent `AsyncIOScheduler` instances** (email, payout, nudge, subscription) all start in-process on FastAPI startup with **no leader election or distributed lock**. This silently assumes exactly one app process/instance forever (see Finding H-2).
- **Deployment topology mismatch.** `deploy/nginx.conf` only proxies `/api/` and serves a handful of static pages; it does **not** route the FastAPI page/redirect endpoints (`/r/{code}`, `/sales/*`, `/affiliate/*`, `/unsubscribe`), so the Docker-Compose deployment would 404 on affiliate referral links. (Production appears to be Render, where FastAPI serves everything — so the compose file is a stale/secondary path.)

## 4. Performance Assessment

Indexing is well thought out (`database.py` creates ~35 indexes, concurrently via `asyncio.gather`, and even backfills `unsubscribe_token` before creating its unique index). Most hot aggregations are single grouped queries rather than per-row loops, and the code comments show performance regressions were actively hunted.

Remaining performance concerns, in rough order of impact:

- **Unbounded in-memory scans.** `admin.py get_analytics_customers` does `db.users.find(query, {"email":1}).to_list(100000)` then an `$in` over every email; `get_sequence_overview` loads every active subscriber via `to_list(100000)`. These are O(all-customers) in memory on each admin page load and will degrade as the customer base grows.
- **N+1 offer lookups.** `admin_get_subscriptions`, `admin_get_subscriptions_kpis`, and `run_daily_subscription_billing` fetch `offers.find_one({"_id": sub["offer_id"]})` once **per subscription** in a loop. Offers are few and static — one `$in` batch would replace N round trips.
- **Per-request recompute with no cache.** `/api/public/sales-count` runs `count_documents` on every call and is polled every 30s by every landing-page visitor; `admin.py list_sales_reps` runs two `count_documents` per rep.
- **`sync_pending_batch` runs on every payout list/get** (`admin_payouts.py`), re-reading all unpaid referrals and rewriting the batch doc even for a read.

None of these are dangerous at current (single-operator, low-volume) scale; they are scale-latent.

## 5. Security Assessment

The app gets several fundamentals right: bcrypt password hashing, HMAC webhook verification that **fails closed**, generic responses on the account-recovery endpoint (no user enumeration), Jinja2 autoescaping for emails, `html.escape()` on names in server-generated emails, security headers middleware, and a startup guard that hard-fails production if the admin password is still the shipped default. Those are real strengths.

The weaknesses:

- **Stored XSS against the admin (High).** Customer/lead/affiliate `name` is free text (only length-validated) and is rendered with `innerHTML` and raw `${...}` interpolation throughout `frontend/admin/dashboard.html` (e.g. recent-sales/lead/customer/affiliate tables, transaction drawer). A buyer who registers with a name like `<img src=x onerror=...>` executes script in the admin's authenticated session when the admin opens the dashboard. `ai_insights` items are also mapped with raw HTML (currently empty, but the sink exists).
- **Rate limiting & IP abuse controls are defeated behind the proxy (High).** `slowapi` uses `get_remote_address` (= `request.client.host`), and lead/webhook/affiliate-registration IP logging all read `request.client.host`. The app is deployed behind a reverse proxy (Render/nginx) but is **not** started with `--proxy-headers` and has no `ProxyHeadersMiddleware`/`forwarded-allow-ips`. So every request appears to originate from the proxy IP: brute-force/registration/checkout limits collapse into one shared bucket (one attacker can exhaust everyone's limit, or the per-IP affiliate-signup cap becomes global), and all stored IPs are useless for fraud analysis.
- **Permanent bearer secrets in URLs (Medium–High).** `users.library_access_token` (`/library?token=…`) and `affiliates.dashboard_token` (`/affiliate/dashboard?token=…`) never expire and grant full access. The affiliate token additionally authorizes `POST /api/affiliate/bank-details` — anyone who obtains the token (email forwarding, browser history, `Referer` leakage, shared device) can **redirect that affiliate's payout bank account**.
- **Unauthenticated MongoDB in `docker-compose.yml` (Medium).** `mongo:7` published on `0.0.0.0:27017` with no credentials and `restart: always`.
- **Live credentials present in the working tree (Informational/hygiene).** `.env` in the project root contains real-looking Atlas connection string (with password), SMTP password, and Flutterwave client secret. It is correctly git-ignored and **not** tracked, but it sits in the deliverable folder and is loaded by `tests/conftest.py` if present.
- **Non-constant-time admin password compare (Low).** `admin_login` compares the env password with `==`; timing side-channel is marginal but trivially avoidable with `secrets.compare_digest`.
- **`MAX_FILE_SIZE_MB` is dead config (Low).** `admin.py upload_product` never enforces it and only checks the `.pdf` filename suffix, not content type or size.

## 6. Code Quality Assessment

Readability is above average for a solo project: descriptive names, module docstrings that explain *why*, and post-mortem comments on past incidents. Weaknesses: `frontend/admin/dashboard.html` is a **2,064-line** single file mixing markup, styles, and ~32 `innerHTML` render sites; `routes/admin.py` is **1,188 lines** spanning login, analytics, products, customers, affiliates, subscriptions, team, and the email-sequence monitor (it embeds a hardcoded 52-entry `_SEQ_SUBJECTS` list that duplicates the subjects already in `email_scheduler.EMAIL_SEQUENCE` — two sources of truth that can drift). `TokenResponse` is defined twice (schemas + inline in `sales.py`). Some endpoints raise bare `Exception` (e.g. `sales.py process_checkout_payment`) which surfaces as an opaque 500.

## 7. Maintainability Assessment

The single biggest maintainability hazard is the **tracking-vs-automation split-brain** in the affiliate/commission domain: a future change to "how commissions get marked paid" must be made consistently across `payout_service`, two admin endpoints, and the health service, or money state drifts. The **hardcoded/duplicated sequence metadata** and **dead `admin_analytics.py`** are traps for the next reader. The **single-process scheduler assumption** is an invisible constraint — nothing documents that the app must never be scaled to >1 instance, and the failure mode (double billing) is silent. Mixed **naive vs. timezone-aware datetimes** (`affiliate_health_service.py` deliberately uses naive `datetime.utcnow()` to match Motor's returns, while everything else is aware) is fragile and one refactor away from a `TypeError`.

## 8. Detailed Findings

Severity: **Critical / High / Medium / Low / Informational**. Confidence: **High / Medium / Low**.

---

### H-1 — Two subsystems both settle affiliate commissions → double-payment pathway
**Severity: High · Confidence: High**
**Files:** `services/payout_service.py` (`send_batch`, `withdraw_settlement_share`), `routes/admin_payouts.py`, `routes/affiliates.py` (`mark_commission_paid`), `routes/admin.py` (`mark_affiliate_payout`, lines ~736), `services/flutterwave.py` (`create_transfer`).
**Root cause:** The program was originally "tracking only" (admin pays out-of-band, then flips a flag). An automated Flutterwave Transfers payout batch system was later added **without retiring the manual flag-flipping endpoints**. Both mutate `referrals.commission_status`.
**Impact / reproduction:** An admin marks an affiliate "paid" manually (e.g. `POST /affiliates/{code}/mark-payout`) after sending money by hand; the same unpaid referrals were (or later are) also included in an automated `send_batch`, which actually transfers again — or vice versa. There is no shared lock or single settlement authority. Also `mark_affiliate_payout` uses `{"commission_status": {"$ne": "paid"}}`, which can flip referrals that a batch is mid-processing.
**Note:** `send_batch` generates a **fresh random reference per item on every approve**, so Flutterwave's reference-based idempotency does **not** protect against a re-approve/double-click — the same batch approved twice can pay twice.

### H-2 — In-process schedulers with no leader election → duplicate billing/payouts on scale-out
**Severity: High · Confidence: Medium** (High if ever run with >1 instance/worker)
**Files:** `main.py` startup, `workers/*_scheduler.py`.
**Root cause:** All four `AsyncIOScheduler`s start on every process. Correct for a single Render instance; unsafe the moment the app runs 2+ instances or gunicorn workers.
**Impact:** Email queue is protected (atomic `find_one_and_update` claim in the DB), so emails stay safe across processes. **Subscription billing and payout-batch build are not** — each instance would independently bill/build. The payout *builder* has a same-calendar-day guard (partial protection); subscription billing has none.

### H-3 — Recurring subscription billing has no idempotent claim → double-charge risk
**Severity: High · Confidence: High**
**File:** `workers/subscription_scheduler.py` (`run_daily_subscription_billing`).
**Root cause:** The job selects `status:"active", next_charge_date <= now`, charges the saved card, then updates `next_charge_date`. There is **no atomic "claim this billing period"** before charging (unlike `complete_payment`'s reference-index claim). Each renewal reference is `SUB-REN-{id}-{random}`, so Flutterwave sees a **new** idempotency key each time.
**Impact / reproduction:** (a) Two overlapping runs (H-2, or a manual trigger racing the 1 AM cron) both see the same due subscription and both charge it. (b) Single instance: if `charge_token` succeeds but the subsequent `next_charge_date` update fails/crashes, the next run re-charges. Customer is billed twice with no dedup.

### H-4 — Stored XSS against admin via unescaped customer names
**Severity: High · Confidence: High**
**File:** `frontend/admin/dashboard.html` (render sites ~948, 966, 1050, 1085, 1202, 1228, 1300; also sales `prospect_name`, affiliate `name`).
**Root cause:** Free-text `name` (validated only for length in `schemas.py`) is injected via `innerHTML`/template literals without escaping.
**Impact:** A malicious buyer/affiliate/lead stores a script payload in `name`; it executes in the admin's authenticated browser session on dashboard load (session-token theft, actions-as-admin). This crosses a trust boundary (attacker-controlled input → privileged viewer).

### H-5 — Rate limiting and IP-based abuse controls ineffective behind proxy
**Severity: High · Confidence: High**
**Files:** `utils/rate_limit.py`, `main.py`, all `@limiter.limit(...)` routes, `routes/payments.py`/`affiliate_public.py`/`tracking.py` (IP logging), `deploy/nginx.conf`.
**Root cause:** `get_remote_address`/`request.client.host` read the socket peer, which is the proxy. No `--proxy-headers`, no `ProxyHeadersMiddleware`, no trusted `X-Forwarded-For` parsing.
**Impact:** Login (10/min), checkout (10/min), sales-register (5/hr), and the per-IP affiliate-signup cap (5/hr) all key on the proxy IP → effectively a single global bucket. Brute-force protection is defeated/mis-scoped, and every stored IP is the proxy's.

### M-1 — Real (non-mock) sales-rep card checkout appears broken
**Severity: Medium · Confidence: Medium**
**File:** `routes/sales.py` (`process_checkout_payment`).
**Root cause:** The charge payload sends `"customer_id": lead["prospect_email"]` — an email string where Flutterwave expects a real customer id (everywhere else the code first calls `create_flw_customer` to obtain one). Only the `mock-payment-method-id` dev path is exercised by tests.
**Impact:** Live sales-rep card charges likely fail at the gateway. The subscription-channel revenue path may be non-functional in production, silently (bare `Exception` → 500).

### M-2 — Contradictory in-code documentation on download-link lifetime
**Severity: Medium (correctness-of-reasoning) · Confidence: High**
**Files:** `utils/security.py` (`create_download_token`), `routes/library.py` (`download_file`).
**Root cause:** `create_download_token` **does** set `exp = now + JWT_DOWNLOAD_EXPIRE_MINUTES` (10 min), but the comment in `download_file` asserts the token *"has no separate time-based expiry … remains valid indefinitely."* The behavior (10-minute, reusable link) is fine; the comment is wrong and will mislead the next engineer into a bad decision.

### M-3 — Permanent bearer tokens in URLs (library + affiliate dashboard)
**Severity: Medium · Confidence: High**
**Files:** `routes/library.py`, `routes/affiliate_dashboard.py`.
**Root cause:** `library_access_token` and `dashboard_token` never expire and are passed as query params. The affiliate token authorizes bank-detail changes.
**Impact:** Token leakage (history, `Referer`, forwarded email, shared device) = durable account access; for affiliates, attacker can rewrite payout bank details. No rotation/expiry/re-auth.

### M-4 — Unauthenticated MongoDB and broad port exposure in docker-compose
**Severity: Medium · Confidence: High**
**File:** `deploy/docker-compose.yml`.
**Root cause:** `mongo:7` with no credentials, `27017:27017` published on all interfaces; backend `8000:8000` also public alongside nginx.
**Impact:** If this compose is ever used on a reachable host, the database is open.

### M-5 — Unbounded in-memory scans and N+1 offer lookups
**Severity: Medium · Confidence: High**
**Files:** `routes/admin.py` (`get_analytics_customers`, `get_sequence_overview`), `admin_get_subscriptions*`, `subscription_scheduler.py`.
**Root cause:** `to_list(100000)` over full collections; per-row `offers.find_one` in loops.
**Impact:** Admin dashboard latency and memory grow linearly with customers/subscribers.

### M-6 — `MAX_FILE_SIZE_MB` not enforced; weak upload validation
**Severity: Medium · Confidence: High**
**File:** `routes/admin.py` (`upload_product`).
**Root cause:** Config exists but is never checked; only `.pdf` filename suffix is validated (no size cap, no content sniff). Admin-only, so exposure is limited, but a large upload blocks disk and the config is misleadingly dead.

### M-7 — Nginx deployment does not route FastAPI page/redirect endpoints
**Severity: Medium · Confidence: High**
**File:** `deploy/nginx.conf`.
**Root cause:** Only `/api/` is proxied; `/r/{code}`, `/sales/*`, `/affiliate/*`, `/unsubscribe` are FastAPI routes that nginx neither serves nor proxies.
**Impact:** In the Docker-Compose topology, affiliate referral links and several flows 404. (Mitigated only because production runs FastAPI directly.)

### L-1 — Duplicate sequence-subject source of truth
**Severity: Low · Confidence: High** — `admin.py _SEQ_SUBJECTS` duplicates `email_scheduler.EMAIL_SEQUENCE` subjects; they can drift.

### L-2 — Dead router file — `routes/admin_analytics.py` (600 lines) not wired up; duplicates live logic. Decide: delete or adopt.

### L-3 — Mixed naive/aware datetimes — `affiliate_health_service.py` uses naive `datetime.utcnow()` by design; fragile against the timezone-aware convention elsewhere.

### L-4 — Non-constant-time admin password compare (`admin.py admin_login`, `==`).

### L-5 — Duplicate/overlapping "mark paid" admin endpoints keyed by code vs id (`admin.py` vs `affiliates.py`) — confusing surface even setting aside H-1.

### L-6 — Bare `Exception` raises in request handlers (`sales.py`) produce opaque 500s instead of a mapped `HTTPException`.

### L-7 — Weak password policy — `min_length=6` for admin/sales credentials; startup check only detects the *shipped default*, not weak custom values.

### Informational
- **I-1** Live secrets sit in the working-tree `.env` (git-ignored, untracked) — rotate if this folder was ever shared, and confirm it is never bundled into an image (it is `COPY`-excluded in the Dockerfile; compose injects via `env_file`).
- **I-2** `get_public_sales_count` returns a hardcoded `38` fallback when DB is down — a fabricated social-proof number; acceptable but worth a conscious call.
- **I-3** `GZipMiddleware` + `X-Process-Time` on every response is fine; note `X-Process-Time` leaks timing info (negligible).
- **I-4** `library.get_library` lists all active products to any valid token holder regardless of `purchased_products`; actual file access is correctly gated in `sign_download`, so this is a cosmetic over-share only.

## 9. Prioritized Remediation Roadmap

*(High-level only, per the brief — no implementation detail.)*

**Phase 1 — Critical / money & trust integrity**
1. Resolve the commission split-brain (**H-1**): designate a single settlement authority, make batch approval an atomic compare-and-swap with a stable per-item reference, and reconcile/retire the manual mark-paid endpoints.
2. Make subscription billing idempotent (**H-3**): claim the billing period atomically before charging; use a deterministic idempotency key.
3. Escape all user-controlled strings in the admin dashboard (**H-4**).
4. Restore true client IP behind the proxy so rate limits/abuse controls work (**H-5**).

**Phase 2 — Stability & concurrency**
5. Decide the scaling model and gate schedulers behind a single-leader lock (or move them to a dedicated worker) (**H-2**).
6. Fix or explicitly disable the live sales-rep card checkout (**M-1**).
7. Lock down deploy: Mongo auth + port exposure, and align nginx routing with FastAPI's routes (**M-4, M-7**).

**Phase 3 — Performance**
8. Replace `to_list(100000)` scans with paginated/aggregated queries; batch the N+1 offer lookups; add light caching to public counters (**M-5**).

**Phase 4 — Maintainability & correctness hygiene**
9. Token lifetime/rotation for library + affiliate dashboard links (**M-3**).
10. Enforce upload size/content limits (**M-6**); fix the misleading download-link comment (**M-2**); single-source the sequence metadata (**L-1**); remove or adopt the dead analytics router (**L-2**); normalize datetimes (**L-3**).

**Phase 5 — Nice-to-have**
11. Constant-time admin compare, stronger password policy, mapped exceptions, secret rotation/hygiene, decide on hardcoded social-proof fallbacks (**L-4, L-6, L-7, I-1, I-2**).

## 10. Risks If Left Unfixed

- **Financial loss / disputes:** double-charged subscribers (**H-3**) and double-paid affiliates (**H-1**), each amplified the moment the app is scaled beyond one instance (**H-2**). These are the highest-consequence risks and are invisible until they happen.
- **Account/admin compromise:** stored XSS (**H-4**) can hand an attacker the admin session; leaked affiliate tokens (**M-3**) can reroute payouts.
- **Abuse at scale:** defeated rate limiting (**H-5**) leaves login, checkout, and signup open to scripted abuse and skews all IP-based analytics/fraud signals.
- **Silent revenue leak:** a non-working live sales checkout (**M-1**) could be dropping subscription conversions with only an opaque 500 as evidence.
- **Operational drag:** growing dashboard latency (**M-5**), split-brain commission logic, and duplicated/dead code (**L-1, L-2, H-1**) compound maintenance cost and raise the odds of a regression in the money paths specifically.

---

*Verification performed:* all backend Python compiles cleanly (`py_compile`, no syntax errors); router wiring, auth gating, index definitions, proxy-header handling, XSS sinks, and git-tracking of `.env` were each confirmed directly against source rather than inferred. Findings reflect static analysis; the concurrency-dependent items (H-2, H-3, H-1 double-approve) are reasoned from the code paths and would be worth reproducing under a load/concurrency test before and after the fix.
