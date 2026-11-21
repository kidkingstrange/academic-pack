# Existing Feature Inventory & Migration Requirements

## 1. Feature Classification Matrix

| Feature Module | Business Purpose | Current Implementation | Migration & Modernization Target | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **Product Catalogue & Display** | Browse books and bundle packages | Static HTML landing pages + `products.json` catalog | Next.js Server Components + Flutter Catalog View | P0 (Critical) |
| **Tiered Pricing & Promo Logic** | ₦5,000 promo vs ₦20,000 standard price | Server-enforced via `config.py` & `payments.py` | Centralized pricing API route shared by Web & Mobile | P0 (Critical) |
| **Shopping Cart & Checkout** | Initiate purchase for single book or bundle | Modal checkout with Paystack popup / Flutterwave | Universal Checkout Component + Flutter Native Sheet | P0 (Critical) |
| **Payment Verification** | Verify bank/card charge server-side | Webhook handlers & `/api/payments/verify` | Provider-agnostic payment service (Paystack/Flutterwave) | P0 (Critical) |
| **Student Digital Library** | Customer reads & downloads purchased PDFs | `library.html` with signed expiring JWT tokens | Next.js Protected Route + Flutter In-App PDF Reader | P0 (Critical) |
| **Automated Drip Curriculum** | 52-week educational retention sequence | `db.subscribers` + APScheduler `email_scheduler.py` | Retain FastAPI queue worker / Shared Background Worker | P1 (High) |
| **AI Marketing & Campaigns** | Retain buyers, generate repeat sales | `marketing_service.py` + Admin UI iframe preview | Next.js Admin Panel + Automated Lifecycle Trigger | P1 (High) |
| **Affiliate System** | 60% commission referral marketing | `affiliates.py`, `affiliate_dashboard.html`, milestones | Next.js Affiliate Portal + Flutter Affiliate Tab | P1 (High) |
| **Sales Rep Subscriptions** | Recurring sales agent channel | Flutterwave tokenized recurring charges | Web & Mobile shared subscription billing | P2 (Medium) |
| **Abandoned Cart Recovery** | Re-engage drop-offs after 1h & 24h | `abandoned_transactions` + auto-healing cron | Shared Event-Driven Cart Abandonment Pipeline | P1 (High) |
| **Verified Customer Reviews** | Social proof on landing pages | `reviews.py` with signed customer purchase hash | Next.js Review Component + Flutter Rating Widget | P1 (High) |
| **SEO Blog Engine (400+ Posts)** | Organic search customer acquisition | 418 HTML posts in `/blog/academics/` | Next.js ISR (Incremental Static Regeneration) | P0 (Critical) |
| **Admin Operations Dashboard** | Sales, payouts, order ledger, content CMS | `admin/dashboard.html` with vanilla JS DOM | Next.js Admin Dashboard with App Router | P1 (High) |

---

## 2. Canonical Product Offerings Inventory

The platform currently sells **13 canonical offerings** that have physical, deliverable PDF manuals in the repository:

1. **The Academic Comeback Package (Bundle)** (7-in-1 Study System: ₦5,000 / $15 promo, ₦20,000 regular).
2. **How to Close High-Paying Clients in the DMs** (Sales & Copywriting: ₦5,000 / $15).
3. **What to Do When Your Boss Is Angry With You** (Workplace Diplomacy: ₦5,000 / $15).
4. **How to Do Your Ideas** (Execution & Prototyping: ₦5,000 / $15).
5. **What to Do After a Breakup** (Emotional Reset & Focus: ₦5,000 / $15).
6. **Quitting The Handjob** (Dopamine Reset & Habit Elimination: ₦5,000 / $15).
7. **Get Good at Hard Things** (Cognitive Stamina & Deep Work: ₦5,000 / $15).
8. **Focus Like a Monk in a Discotheque** (Radical Concentration: ₦5,000 / $15).
9. **How to Start Studying When You Have Zero Motivation** (Overcoming Inertia: ₦5,000 / $15).
10. **The First-Class Student Playbook** (High-Yield Academic Tactics: ₦5,000 / $15).
11. **Retain 90 Percent of Everything You Read** (Memory & Active Recall: ₦5,000 / $15).
12. **Master Any Course in 14 Days** (Rapid Exam Deconstruction: ₦5,000 / $15).
13. **Turn Past Questions into an Unfair Advantage** (Strategic Exam Prep: ₦5,000 / $15).

*Note: 18 additional titles defined in `products.json` represent upcoming masterclasses and are treated as Pre-Orders / Waitlists until local PDF assets are supplied.*

---

## 3. Critical E-Commerce Flow Details

### A. The Checkout & Delivery Pipeline
1. **Initiation:** Customer selects product $\rightarrow$ Client submits email, name, product slug, and affiliate code (if cookie present) to `/api/payments/initialize`.
2. **Pending Registration:** Server saves `pending_payments` record with deterministic reference (`ACP-...`) and price independently verified from server config.
3. **Payment Execution:** Customer completes payment via Paystack Inline or Flutterwave Modal.
4. **Verification & Fulfillment:**
   - Webhook or client verification triggers `verify_payment()`.
   - Atomic state update moves record to `payments` with `status: "success"`.
   - Customer account is created or updated in `users` (`purchased_products` appended).
   - Unique, secure `library_access_token` is generated and assigned.
   - Enrolled in 52-week automated curriculum in `subscribers`.
   - Welcome/Access email enqueued in `email_queue`.
   - If affiliate code was present, commission recorded in `referrals`.
   - Server-side Meta CAPI `Purchase` event dispatched.
5. **Access:** Customer accesses `/library.html?token=...` to read online or download watermarked PDFs.
