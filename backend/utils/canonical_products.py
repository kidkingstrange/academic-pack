"""
Canonical product catalog definitions and helpers for the Scale Group / Academic Comeback platform.
Ensures single-source-of-truth pricing, slugs, and PDF assets across database syncing,
authoritative payment initialization, and delivery.
"""
from typing import Optional, Dict, Any, List

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
