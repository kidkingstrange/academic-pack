# BUILD PROMPT — "Master's Eye View" admin command center

## ROLE & OBJECTIVE
You are a senior full-stack + UX engineer. Add a new feature to the existing admin dashboard called the **Master's Eye View** — a single command-center home screen that lets the site owner (non-technical) *see and reach everything on the entire website from one place*, understand how the parts connect, and glance at the live health of each area. It must be **extensible by design**: when new pages, tools, or systems are added to the site in the future, they appear in this view by adding **one registry entry**, not by rewriting the hub. Do not break any existing functionality.

## THE PROBLEM THIS SOLVES
The owner doesn't have a mental map of the site and struggles to navigate from one area to another. The site will keep growing more complex. They need (a) a categorized, plain-English directory of *every* destination, (b) one-click navigation to any of them, (c) live status signals so "seeing everything" means seeing real state, not just links, and (d) a structure that scales as features are added.

## STACK & CONVENTIONS (match these — do not introduce a framework)
- Frontend is static HTML + vanilla JS served by FastAPI. The admin dashboard is `frontend/admin/dashboard.html` (a large single file). Admin auth token lives in `sessionStorage` as `admin_token`; API calls send `Authorization: Bearer <token>`.
- The dashboard already switches between sections via a `switchSection('<key>')` function. Existing sections: `dashboard`, `sales`, `customers`, `affiliates`, `payouts`, `sequence`, `subscriptions`, `team`. Do not remove or rename these.
- Design system: CSS variables in `frontend/css/main.css` and the dashboard's own styles — use the existing tokens (`--gold`, `--gold-l`, `--ink`, `--surface`, `--text`, `--red`, `--green`, `--radius`, `--shadow`, etc.). Keep the dark premium look; do not restyle the whole dashboard.
- Backend is FastAPI + MongoDB (Motor). Admin endpoints live under `/api/admin`. Reuse existing endpoints and aggregation logic; do not duplicate business logic.
- Mobile-first: the owner will often view this on a phone. It must be fully responsive.

## THE FULL SITE INVENTORY (day-one contents of the Master's Eye View)
Seed the registry with **all** of the following so the map is complete on launch. Group them into the categories shown.

**A. Admin sections (in-dashboard, navigate via `switchSection('<key>')`):**
- `dashboard` — Overview: revenue, sales, conversion, recent activity.
- `sales` — Sales & Orders: every transaction; inspect a sale; resend access email; refund; notes.
- `customers` — Customers: customer list, 360° profiles, spend, tags, notes.
- `sequence` — Email Sequence Monitor: the 52-email curriculum health, per-subscriber progress, resend stuck emails.
- `affiliates` — Affiliates Engine: affiliate list, clicks/conversions/commission, edit rates, activate/suspend, affiliate health.
- `payouts` — Payouts: build/approve affiliate payout batches; owner settlement withdrawal.
- `subscriptions` — Subscriptions: recurring plans, MRR/KPIs, cancel.
- `team` — Team Members: sales reps — create, activate/suspend, reset password.

**B. Public & customer-facing pages (navigate by opening the URL in a new tab):**
- `/` — Landing / sales page (the funnel the customer sees).
- `/welcome` — Post-purchase welcome page.
- `/library` — Customer library (where buyers read their books; requires a customer token).
- `/affiliate/register` — Public affiliate signup.
- `/affiliate/dashboard` — Affiliate's own stats page (requires their dashboard token).
- `/sales` — Sales-rep login.
- `/sales/register` — Sales-rep self-registration.
- `/sales/dashboard` — Sales-rep dashboard.
- `/sales/checkout` — Sales-rep-generated checkout link.
- `/sales/cancel` — Subscription cancellation page.
- `/r/{code}` — Affiliate referral redirect (note: needs a real code; show as informational).
- `/unsubscribe` — Email unsubscribe page.
- `/admin` — Admin login.

**C. Systems running in the background (informational + status, not always a page):**
- Email queue & 52-email scheduler (runs every 5 min) — surfaces via the `sequence` section.
- Payout batch builder (1st & 15th) — surfaces via `payouts`.
- Affiliate nudge scheduler (daily).
- Subscription billing scheduler (daily) — surfaces via `subscriptions`.
- Payment webhook + flagged payments (payments needing manual review).

Write every description in **plain English for a non-technical owner** ("What this is / what you do here"), not developer jargon.

## WHAT TO BUILD

### 1. A single site registry (the extensibility core — most important part)
Create one source-of-truth manifest describing every destination — e.g. `frontend/admin/site-registry.js` (a plain JS array/object loaded by the dashboard), each entry:
```
{
  id: "sales",
  title: "Sales & Orders",
  description: "Every purchase. Open one to inspect it, resend the access email, or refund.",
  category: "Money & Orders",
  type: "admin-section" | "public-page" | "external" | "system",
  target: "sales"            // switchSection key, OR a URL for pages/external
  icon: "💳"                 // or an icon class already available
  metric: "sales_today"      // optional: key into the live-overview payload (see #3)
  status_key: "flagged_payments" // optional: a warning signal to badge this card
}
```
Adding a future feature must require **only**: append one entry here (and optionally one number to the overview endpoint in #3). Document this contract in a comment block at the top of the registry file and in the code that renders it. Group order and categories are derived from the registry, not hardcoded in the view.

### 2. The Master's Eye View screen (the new default admin home)
- Add it as the **first** item in the admin nav and make it the landing screen after login (demote the current `dashboard`/Overview to a normal section, or nest it — but Master's Eye View is what the owner lands on).
- Render the registry **grouped by category** into clean cards. Suggested categories/order: *Money & Orders* (sales, payouts, subscriptions), *People* (customers, affiliates, team), *Communication* (email sequence, nudges, unsubscribe), *Public Pages* (landing, welcome, library, affiliate/sales pages), *System Health* (schedulers, webhook/flagged payments).
- Each card shows: icon, title, plain-English description, a **live status chip** (from #3), and clicking it either calls `switchSection(target)` (admin sections) or opens the URL in a new tab (pages), or is informational (systems).
- Add a **search/filter box** at the top that instantly filters cards by title/description so the owner can type "refund" or "affiliate" and jump straight there.
- Add a small **"How it all connects" panel**: three simple visual journey strips — (1) Customer: Landing → Checkout → Welcome → Library → Email sequence; (2) Affiliate: Register → Referral link → Sale attributed → Payout; (3) Sales rep: Register → Approved by admin → Generates checkout → Subscription. Each node links to the relevant admin section. This gives the owner the A→B mental model they're missing.

### 3. One live-overview endpoint (efficient, reuse existing logic)
- Add a single admin-protected endpoint (e.g. `GET /api/admin/master-overview`) that returns, in one response, the headline numbers the cards bind to — reusing existing aggregations (do not rewrite them). Include at least: sales today / revenue today, total customers, pending + failed emails, subscribers behind in the sequence, active/past-due subscriptions, unpaid commission owed, pending payout batches, flagged payments needing review, new leads today, active affiliates.
- The Master's Eye View makes **one** call to this endpoint on load and distributes values to cards via each entry's `metric`/`status_key`. Do not fire a separate request per card. Cache briefly and add a manual Reload button.
- Cards with a `status_key` that indicates a problem (e.g., failed emails > 0, flagged payments > 0, payouts owed > 0) show a colored warning badge so the owner immediately sees what needs attention.

## CONSTRAINTS (must respect)
- **Admin-only:** reuse the existing admin auth gate; the new endpoint requires admin (same dependency as other `/api/admin` routes). No data exposed without it.
- **Reuse, don't duplicate:** pull numbers from existing aggregation logic; don't re-implement analytics.
- **Don't break the 8 existing sections** or their deep-links; `switchSection` must keep working for all of them.
- **No new frameworks or heavy dependencies;** vanilla JS + existing styles only. Keep it fast on mobile and inside in-app browsers.
- **Truthful status:** show real values from the DB; if a value can't be computed, show a neutral state, never a fabricated number.
- **Extensibility is a hard requirement:** verify that adding a new registry entry (with no other code change) makes a new card appear correctly.

## VERIFICATION (done means all pass)
1. After admin login, the Master's Eye View is the landing screen and lists **every** destination from the inventory above, grouped and described in plain English.
2. Clicking an admin-section card navigates via `switchSection` to the correct working section; clicking a public-page card opens the correct URL; system cards show status without breaking.
3. The search box filters cards live by name/description.
4. Live numbers load from a **single** `/api/admin/master-overview` call; warning badges appear when there are failed emails, flagged payments, or commission owed; a Reload button refreshes them.
5. The "How it all connects" journeys render and their nodes link to the right sections.
6. **Extensibility test:** add one dummy registry entry → confirm a new card appears in the right category with working navigation, with no other code change → then remove the dummy.
7. All 8 existing admin sections still work exactly as before; no JS console errors; fully responsive at ~360–430px.
8. The new endpoint is admin-protected (401 without a valid admin token) and reuses existing aggregations (no duplicated business logic).
9. Report which files changed and confirm behavior by actually loading the dashboard — not just that it compiles.
