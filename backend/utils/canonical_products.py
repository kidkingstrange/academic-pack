"""
Canonical product catalog definitions and helpers for the Scale Group / Academic Comeback platform.
Ensures single-source-of-truth pricing, slugs, and PDF assets across database syncing,
authoritative payment initialization, and delivery.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from ..config import get_settings

CANONICAL_PRODUCTS: List[Dict[str, Any]] = [
    {
        "order": 1,
        "title": "Get Good at Hard Things",
        "description": "A system for academic and skill excellence through discipline, mental depth, and deliberate effort.",
        "file_path": "get_good_at_hard_things.pdf",
        "aliases": ["GET GOOD AT HARD THINGS by David Itoya.pdf", "get_good_at_hard_things.pdf"],
        "slug": "get-good-at-hard-things",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 2,
        "title": "How to Score High in Any Exam",
        "description": "Proven strategies, smart study techniques, and practical exam preparation protocols to achieve top results.",
        "file_path": "how_to_score_high_in_any_exam.pdf",
        "aliases": ["HOW TO PASS ANY EXAM WITH HIGH SCORES.pdf", "how_to_score_high_in_any_exam.pdf"],
        "slug": "how-to-score-high-in-any-exam",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 3,
        "title": "How to Balance Your Academics and Your Business",
        "description": "A practical guide to excelling in school, growing your business, and building the life you want without burnout.",
        "file_path": "balance_academics_and_business.pdf",
        "aliases": ["HOW TO BALANCE YOUR ACADEMICS AND YOUR BUSINESS.pdf", "balance_academics_and_business.pdf"],
        "slug": "balance-academics-and-business",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 4,
        "title": "Result-Oriented Learning",
        "description": "Know exactly what to study for exams. Eliminate wasted effort and focus on high-yield topic mastery.",
        "file_path": "results_oriented_learning.pdf",
        "aliases": ["RESULT-ORIENTED LEARNING.pdf", "results_oriented_learning.pdf"],
        "slug": "result-oriented-learning",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 5,
        "title": "30-Day Study Tracker",
        "description": "Daily progress & discipline system to build consistent study habits, track syllabus coverage, and stay accountable.",
        "file_path": "30_day_study_tracker.pdf",
        "aliases": ["30-Day Study Tracker.pdf", "30_day_study_tracker.pdf"],
        "slug": "30-day-study-tracker",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 6,
        "title": "Focus Template",
        "description": "Deep work & distraction elimination system to block out digital noise, build focus stamina, and double study output.",
        "file_path": "focus_template.pdf",
        "aliases": ["🎯 Focus Template.pdf", "focus_template.pdf"],
        "slug": "focus-template",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 7,
        "title": "Exam Survival Guide",
        "description": "High-stakes preparation & tactical performance protocol for final exams, professional certifications, and tests.",
        "file_path": "exam_survival_guide.pdf",
        "aliases": ["🔥 Exam Survival Guide.pdf", "exam_survival_guide.pdf"],
        "slug": "exam-survival-guide",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 8,
        "title": "Quitting The Handjob",
        "description": "How to Stop Masturbation and Pornography Addiction Forever. A neurochemical and behavioral recovery blueprint for lasting freedom.",
        "file_path": "Quitting_The_Handjob_David_Itoya.pdf",
        "aliases": ["Quitting_The_Handjob_David_Itoya.pdf", "quitting_the_handjob.pdf", "quitting-the-handjob.pdf", "Quitting The Handjob.pdf"],
        "slug": "quitting-the-handjob",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 9,
        "title": "How to Close High-Paying Clients in the DMs",
        "description": "A tactical manual for young corporate professionals and founders to turn direct messages into high-ticket clients without being pushy or awkward.",
        "file_path": "How to Close High-Paying Clients in the DMs - David Itoya.pdf",
        "aliases": [
            "How to Close High-Paying Clients in the DMs - David Itoya.pdf",
            "How to Close High-Paying Clients in the DMs.pdf",
            "how-to-close-high-paying-clients-in-the-dms.pdf",
            "high_paying_clients_in_dm.pdf",
            "clients-in-dm.pdf"
        ],
        "slug": "how-to-close-high-paying-clients-in-the-dms",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 10,
        "title": "How to Do Your Ideas",
        "description": "The easiest, proven ways to stop overthinking, build momentum, and turn your inspiration into real-world execution.",
        "file_path": "How to Do Your Ideas - David Itoya.pdf",
        "aliases": [
            "How to Do Your Ideas - David Itoya.pdf",
            "How to Do Your Ideas.pdf",
            "how-to-do-your-ideas.pdf",
            "do-your-ideas.pdf"
        ],
        "slug": "how-to-do-your-ideas",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 11,
        "title": "What to Do After a Breakup",
        "description": "How to be genuinely happy without your ex. A psychology-grounded roadmap to process heartbreak, regain self-respect, and heal completely.",
        "file_path": "What to Do After a Breakup - David Itoya.pdf",
        "aliases": [
            "What to Do After a Breakup - David Itoya.pdf",
            "What to Do After a Breakup.pdf",
            "what-to-do-after-a-breakup.pdf",
            "breakup-recovery.pdf"
        ],
        "slug": "what-to-do-after-a-breakup",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
    {
        "order": 12,
        "title": "What To Do When Your Boss Is Angry With You",
        "description": "The workplace survival and advancement playbook to defuse tension, rebuild trust, and turn managerial conflict into career advancement.",
        "file_path": "What To Do When Your Boss Is Angry With You - David Itoya.pdf",
        "aliases": [
            "What To Do When Your Boss Is Angry With You - David Itoya.pdf",
            "What To Do When Your Boss Is Angry With You.pdf",
            "what-to-do-when-your-boss-is-angry-with-you.pdf",
            "how-to-turn-your-boss-into-your-biggest.pdf",
            "angry-boss.pdf"
        ],
        "slug": "what-to-do-when-your-boss-is-angry-with-you",
        "price_naira": 5000,
        "price_usd": 15.0,
    },
]


def get_canonical_product(slug: Optional[str] = None, title: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Resolve a canonical product definition by slug or title."""
    clean_slug = (slug or "").strip().lower()
    clean_title = (title or "").strip().lower()

    if clean_slug:
        for p in CANONICAL_PRODUCTS:
            if (p.get("slug") or "").lower() == clean_slug:
                return p

    if clean_title:
        for p in CANONICAL_PRODUCTS:
            if (p.get("title") or "").lower() == clean_title:
                return p
            for alias in p.get("aliases", []):
                if alias.lower() == clean_title or alias.lower().startswith(clean_title):
                    return p

    return None


def get_canonical_price(slug: Optional[str] = None, title: Optional[str] = None, currency: str = "NGN") -> float:
    """Return canonical authoritative price in NGN or USD, defaulting strictly to 5,000 NGN / 15.0 USD."""
    prod = get_canonical_product(slug=slug, title=title)
    is_usd = (currency or "").strip().upper() == "USD"
    if prod:
        return float(prod["price_usd"] if is_usd else prod["price_naira"])
    return 15.0 if is_usd else 5000.0


# Initialize default SKUs across canonical products catalog
for _p in CANONICAL_PRODUCTS:
    _p.setdefault("sku", f"BOOK-{_p['slug'].upper()}")


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp or date string into a UTC-aware datetime."""
    if not dt_str:
        return None
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def is_academic_comeback_promo_active(now_dt: Optional[datetime] = None) -> bool:
    """
    Returns True if the Academic Comeback Package promotional pricing (₦5,000)
    is active. Ends strictly on 1st of January 2027 (or configured end date).
    """
    settings = get_settings()
    promo_end = parse_iso_datetime(getattr(settings, "ACADEMIC_COMEBACK_PROMO_END_DATE", None))
    if not promo_end:
        promo_end = datetime(2027, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    if now_dt is None:
        now_dt = datetime.now(timezone.utc)
    elif now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)

    return now_dt < promo_end


def get_package_price(currency: str = "NGN", now_dt: Optional[datetime] = None) -> float:
    """Return authoritative Academic Comeback Package price (₦5,000 promo / ₦20,000 regular)."""
    settings = get_settings()
    is_usd = (currency or "").strip().upper() == "USD"
    if is_academic_comeback_promo_active(now_dt):
        return float(getattr(settings, "PACKAGE_PROMO_PRICE_USD", 15.0) if is_usd else getattr(settings, "PACKAGE_PROMO_PRICE_NAIRA", 5000))
    else:
        return float(getattr(settings, "PACKAGE_REGULAR_PRICE_USD", 40.0) if is_usd else getattr(settings, "PACKAGE_REGULAR_PRICE_NAIRA", 20000))


def build_order_items(
    product_slug: Optional[str] = None,
    product_title: Optional[str] = None,
    product_id: Optional[str] = None,
    tier: Optional[str] = None,
    unit_price: Optional[float] = None,
    quantity: int = 1,
    items: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Build a structured list of purchased items snapshot for a transaction."""
    if items and isinstance(items, list) and len(items) > 0:
        cleaned = []
        for it in items:
            p_id = str(it.get("product_id") or it.get("slug") or "item")
            p_sku = str(it.get("product_sku") or it.get("sku") or f"SKU-{p_id.upper()}")
            p_name = str(it.get("name") or it.get("title") or "Product")
            p_qty = int(it.get("quantity") or 1)
            p_unit = float(it.get("unit_price") if it.get("unit_price") is not None else (it.get("price") or 0.0))
            p_total = float(it.get("total_price") if it.get("total_price") is not None else (p_unit * p_qty))
            cleaned.append({
                "product_id": p_id,
                "product_sku": p_sku,
                "name": p_name,
                "quantity": p_qty,
                "unit_price": p_unit,
                "total_price": p_total,
            })
        return cleaned

    # Check if this is the Academic Comeback Package (flagship bundle)
    is_bundle = (
        not product_slug
        or product_slug.strip().lower() in ("academic-comeback-package", "academic-comeback", "acp")
        or (product_title and "academic comeback" in product_title.lower())
    )

    # Single canonical book resolution
    if not is_bundle and (product_slug or product_title):
        canonical = get_canonical_product(slug=product_slug, title=product_title)
        if canonical:
            price_val = float(unit_price if unit_price is not None else canonical.get("price_naira", 5000.0))
            return [{
                "product_id": str(product_id or canonical.get("slug")),
                "product_sku": canonical.get("sku", f"BOOK-{canonical['slug'].upper()}"),
                "name": canonical["title"],
                "quantity": max(1, int(quantity or 1)),
                "unit_price": price_val,
                "total_price": price_val * max(1, int(quantity or 1)),
            }]
        elif product_title or product_slug:
            name_val = product_title or product_slug.replace("-", " ").title()
            slug_clean = (product_slug or "custom-product").strip().lower()
            price_val = float(unit_price if unit_price is not None else 5000.0)
            return [{
                "product_id": str(product_id or slug_clean),
                "product_sku": f"BOOK-{slug_clean.upper()}",
                "name": name_val,
                "quantity": max(1, int(quantity or 1)),
                "unit_price": price_val,
                "total_price": price_val * max(1, int(quantity or 1)),
            }]

    # Bundle / Academic Comeback Package
    tier_clean = (tier or "complete").strip().lower()
    sku = "ACP-BUNDLE" if tier_clean == "complete" else f"ACP-{tier_clean.upper()}"
    bundle_name = "The Academic Comeback Package"
    if tier_clean == "starter":
        bundle_name = "The Academic Comeback Package (Starter Tier)"
    elif tier_clean == "vip":
        bundle_name = "The Academic Comeback Package (VIP Mentorship Tier)"
    price_val = float(unit_price if unit_price is not None else 5000.0)
    return [{
        "product_id": "academic-comeback-package",
        "product_sku": sku,
        "name": bundle_name,
        "quantity": max(1, int(quantity or 1)),
        "unit_price": price_val,
        "total_price": price_val * max(1, int(quantity or 1)),
    }]


def resolve_payment_items(payment_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Safely resolve structured item list for any payment document.
    Ensures both new payments (with existing 'items') and historical records
    (with only reference, product_slug, book_title, or tier) return exact,
    accurate product name, SKU, quantity, and price.
    """
    if not payment_doc or not isinstance(payment_doc, dict):
        return []

    existing_items = payment_doc.get("items")
    if existing_items and isinstance(existing_items, list) and len(existing_items) > 0:
        return [
            {
                "product_id": str(it.get("product_id") or it.get("slug") or "item"),
                "product_sku": str(it.get("product_sku") or it.get("sku") or "SKU-PROD"),
                "name": str(it.get("name") or it.get("title") or "The Academic Comeback Package"),
                "quantity": int(it.get("quantity") or 1),
                "unit_price": float(it.get("unit_price") if it.get("unit_price") is not None else (it.get("price") or payment_doc.get("amount") or 0.0)),
                "total_price": float(it.get("total_price") if it.get("total_price") is not None else (payment_doc.get("amount") or 0.0)),
            }
            for it in existing_items
        ]

    amt = float(payment_doc.get("amount") if payment_doc.get("amount") is not None else (payment_doc.get("amount_paid") or payment_doc.get("base_price") or 5000.0))
    ref = (payment_doc.get("reference") or "").strip().upper()
    slug = (payment_doc.get("product_slug") or "").strip().lower()
    title = (payment_doc.get("book_title") or payment_doc.get("product_title") or "").strip()

    # Match by slug or title
    if slug or title:
        canon = get_canonical_product(slug=slug, title=title)
        if canon:
            return [{
                "product_id": str(payment_doc.get("product_id") or canon["slug"]),
                "product_sku": canon.get("sku", f"BOOK-{canon['slug'].upper()}"),
                "name": canon["title"],
                "quantity": 1,
                "unit_price": amt,
                "total_price": amt,
            }]
        elif title or slug:
            clean_name = title or slug.replace("-", " ").title()
            return [{
                "product_id": slug or "product",
                "product_sku": f"BOOK-{slug.upper()}" if slug else "BOOK-CUSTOM",
                "name": clean_name,
                "quantity": 1,
                "unit_price": amt,
                "total_price": amt,
            }]

    # Match by reference prefix
    ref_prefix_map = {
        "ACP-QTH-": "quitting-the-handjob",
        "ACP-DMS-": "how-to-close-high-paying-clients-in-the-dms",
        "ACP-IDEA-": "how-to-do-your-ideas",
        "ACP-BRK-": "what-to-do-after-a-breakup",
        "ACP-BOSS-": "what-to-do-when-your-boss-is-angry-with-you",
    }
    for pfx, mapped_slug in ref_prefix_map.items():
        if ref.startswith(pfx):
            canon = get_canonical_product(slug=mapped_slug)
            if canon:
                return [{
                    "product_id": canon["slug"],
                    "product_sku": canon.get("sku", f"BOOK-{canon['slug'].upper()}"),
                    "name": canon["title"],
                    "quantity": 1,
                    "unit_price": amt,
                    "total_price": amt,
                }]

    # Default / bundle purchase (Academic Comeback Package)
    tier = (payment_doc.get("tier") or "complete").strip().lower()
    bundle_sku = "ACP-BUNDLE" if tier == "complete" else f"ACP-{tier.upper()}"
    bundle_name = "The Academic Comeback Package"
    if tier == "starter":
        bundle_name = "The Academic Comeback Package (Starter Tier)"
    elif tier == "vip":
        bundle_name = "The Academic Comeback Package (VIP Mentorship Tier)"

    return [{
        "product_id": "academic-comeback-package",
        "product_sku": bundle_sku,
        "name": bundle_name,
        "quantity": 1,
        "unit_price": amt,
        "total_price": amt,
    }]

