/**
 * Master's Eye View — site registry.
 *
 * This is the single source of truth for every destination on the site
 * that the Master's Eye View hub renders as a card. To add a new feature
 * to the hub in the future, append ONE entry here — nothing in
 * dashboard.html needs to change. Category grouping, ordering, search, and
 * card rendering are all derived from this array, not hardcoded per entry.
 *
 * Entry shape:
 *   id           unique string. For type "admin-section" this MUST match
 *                the section's switchSection() key (e.g. "sales").
 *   title        short card heading.
 *   description  plain English, written for a non-technical site owner —
 *                "what this is / what you do here", not developer jargon.
 *   category     group heading the card renders under. Any string works;
 *                new categories appear automatically. Suggested order:
 *                "Money & Orders", "People", "Communication",
 *                "Public Pages", "System Health".
 *   type         "admin-section" — clicking calls switchSection(target)
 *                "public-page"   — clicking opens target (a URL) in a new tab
 *                "external"      — same as public-page, for fully external links
 *                "system"        — informational only; no click action unless
 *                                  `target` is also set (then behaves like public-page)
 *   target       switchSection key (admin-section) or a URL (everything else).
 *   icon         one emoji, shown at card top-left.
 *   metric       optional. A key into the GET /api/admin/master-overview
 *                payload — its value renders as the card's headline number.
 *   status_key   optional. A key into the same payload — if its value is a
 *                truthy positive number, the card gets a colored warning
 *                badge showing that count. Can be the same key as `metric`
 *                or a different one.
 */
const SITE_REGISTRY = [
  // ── Money & Orders ──────────────────────────────────────────────────────
  {
    id: "dashboard",
    title: "Overview",
    description: "The big-picture snapshot: revenue, sales, conversion rate, and recent activity across the whole business.",
    category: "Money & Orders",
    type: "admin-section",
    target: "dashboard",
    icon: "📊",
    metric: "revenue_today",
  },
  {
    id: "sales",
    title: "Sales & Orders",
    description: "Every purchase, ever. Open one to inspect it, resend the access email, or issue a refund.",
    category: "Money & Orders",
    type: "admin-section",
    target: "sales",
    icon: "💳",
    metric: "sales_today",
  },
  {
    id: "payouts",
    title: "Payouts",
    description: "Build and approve affiliate commission payments, and withdraw your own settlement balance. Every transfer needs your explicit approval — nothing sends automatically.",
    category: "Money & Orders",
    type: "admin-section",
    target: "payouts",
    icon: "🏦",
    metric: "commission_owed",
    status_key: "pending_payout_batches",
  },
  {
    id: "subscriptions",
    title: "Subscriptions",
    description: "Recurring plans: who's active, who's behind on billing, and monthly recurring revenue. Cancel a plan from here.",
    category: "Money & Orders",
    type: "admin-section",
    target: "subscriptions",
    icon: "🔁",
    metric: "active_subscriptions",
    status_key: "past_due_subscriptions",
  },

  // ── People ───────────────────────────────────────────────────────────────
  {
    id: "customers",
    title: "Customers",
    description: "Every customer who's ever bought. Click one to see their full history: what they bought, what they've spent, and notes you've left.",
    category: "People",
    type: "admin-section",
    target: "customers",
    icon: "👥",
    metric: "total_customers",
  },
  {
    id: "affiliates",
    title: "Affiliates",
    description: "Everyone promoting your product for a commission. See clicks, sales, and commission owed; change their rate; pause an affiliate.",
    category: "People",
    type: "admin-section",
    target: "affiliates",
    icon: "📣",
    metric: "active_affiliates",
  },
  {
    id: "team",
    title: "Team Members",
    description: "Your sales staff's accounts — create a new one, suspend someone, or reset a forgotten password.",
    category: "People",
    type: "admin-section",
    target: "team",
    icon: "🧑‍💼",
  },

  // ── Communication ────────────────────────────────────────────────────────
  {
    id: "sequence",
    title: "Email Sequence",
    description: "Health of the 52-email course every customer receives — who's on track, who's fallen behind, and a button to resend a stuck email.",
    category: "Communication",
    type: "admin-section",
    target: "sequence",
    icon: "✉️",
    metric: "subscribers_behind",
    status_key: "failed_emails",
  },
  {
    id: "email-delivery",
    title: "Email Delivery",
    description: "Every welcome and sequence email, tracked proactively — search a customer's full history or spot systemic failures before they go unnoticed for weeks.",
    category: "Communication",
    type: "admin-section",
    target: "email-delivery",
    icon: "📬",
    status_key: "failed_welcome_emails",
  },
  {
    id: "unsubscribe-page",
    title: "Unsubscribe Page",
    description: "The page a customer lands on if they opt out of emails. Needs their personal unsubscribe link to work — this opens the page without one, just to preview it.",
    category: "Communication",
    type: "public-page",
    target: "/unsubscribe",
    icon: "🔕",
  },

  // ── Public Pages ─────────────────────────────────────────────────────────
  {
    id: "landing-page",
    title: "Landing Page",
    description: "The page a visitor sees first — the full sales pitch and checkout button.",
    category: "Public Pages",
    type: "public-page",
    target: "/",
    icon: "🏠",
  },
  {
    id: "welcome-page",
    title: "Welcome Page",
    description: "What a customer sees the moment they've paid, right before reaching their library.",
    category: "Public Pages",
    type: "public-page",
    target: "/welcome",
    icon: "🎉",
  },
  {
    id: "library-page",
    title: "Customer Library",
    description: "Where a paying customer reads/downloads their books. Needs a real customer's access link to open properly.",
    category: "Public Pages",
    type: "public-page",
    target: "/library",
    icon: "📚",
  },
  {
    id: "affiliate-register-page",
    title: "Affiliate Sign-Up",
    description: "The public page where anyone can become an affiliate and get their own referral link.",
    category: "Public Pages",
    type: "public-page",
    target: "/affiliate/register",
    icon: "🖋️",
  },
  {
    id: "affiliate-dashboard-page",
    title: "Affiliate's Own Dashboard",
    description: "What an affiliate sees when they check their own stats. Needs their personal dashboard link to open properly.",
    category: "Public Pages",
    type: "public-page",
    target: "/affiliate/dashboard",
    icon: "📈",
  },
  {
    id: "sales-login-page",
    title: "Sales Rep Login",
    description: "Where your sales reps sign in to their own dashboard.",
    category: "Public Pages",
    type: "public-page",
    target: "/sales",
    icon: "🔑",
  },
  {
    id: "sales-register-page",
    title: "Sales Rep Sign-Up",
    description: "The page a new sales rep uses to create their own account — you still approve them from Team Members before they can log in.",
    category: "Public Pages",
    type: "public-page",
    target: "/sales/register",
    icon: "📝",
  },
  {
    id: "sales-dashboard-page",
    title: "Sales Rep Dashboard",
    description: "What a sales rep sees day to day: their leads and generated checkout links.",
    category: "Public Pages",
    type: "public-page",
    target: "/sales/dashboard",
    icon: "🗂️",
  },
  {
    id: "sales-checkout-page",
    title: "Sales Checkout Link",
    description: "The personalized payment page a sales rep sends a prospect. Needs a real generated link to open properly.",
    category: "Public Pages",
    type: "public-page",
    target: "/sales/checkout",
    icon: "🧾",
  },
  {
    id: "sales-cancel-page",
    title: "Subscription Cancel Page",
    description: "Where a customer confirms cancelling their subscription.",
    category: "Public Pages",
    type: "public-page",
    target: "/sales/cancel",
    icon: "✖️",
  },
  {
    id: "referral-redirect",
    title: "Affiliate Referral Link",
    description: "The link format affiliates share: /r/ followed by their code. Every affiliate gets a unique one — open a specific affiliate's page to test theirs.",
    category: "Public Pages",
    type: "system",
    icon: "🔗",
  },
  {
    id: "admin-login-page",
    title: "Admin Login",
    description: "The sign-in page for this dashboard itself — useful if you need to copy the link for another admin.",
    category: "Public Pages",
    type: "public-page",
    target: "/admin",
    icon: "🛡️",
  },

  // ── System Health ────────────────────────────────────────────────────────
  {
    id: "flagged-payments",
    title: "Payments Needing Review",
    description: "Payment notifications that came in but didn't match an expected order — held here for you to check by hand instead of auto-approving.",
    category: "System Health",
    type: "system",
    icon: "🚩",
    status_key: "flagged_payments",
  },
  {
    id: "affiliate-nudge-scheduler",
    title: "Affiliate Nudge Reminders",
    description: "An automatic once-a-day check that emails any affiliate who signed up but hasn't shared their link yet, encouraging them to get started.",
    category: "System Health",
    type: "system",
    icon: "⏰",
  },
];
