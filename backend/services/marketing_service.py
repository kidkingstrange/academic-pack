"""
AI-Powered E-Commerce Email Marketing and Revenue Generation Engine Service.
Handles product knowledge base retrieval, customer segmentation, AI direct-response
copy generation, campaign creation, preview testing, and queue dispatch.
"""
import re
import secrets
import html
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId

from ..config import get_settings
from ..utils.canonical_products import (
    CANONICAL_PRODUCTS,
    get_canonical_product,
    get_canonical_price,
    get_package_price,
    is_academic_comeback_promo_active,
)
from ..services.email_service import send_email, html_to_text

settings = get_settings()

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# ── Structured Internal Product Knowledge Base ──────────────────────────────
# Single source of truth for the AI marketing engine. Grounded strictly in
# canonical deliverables — zero hallucinated claims, fake discounts, or fabricated bonuses.

PRODUCT_KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    {
        "slug": "academic-comeback-package",
        "title": "The Academic Comeback Package",
        "sku": "ACP-BUNDLE",
        "category": "Academic Performance & High GPA",
        "price_naira": 5000,
        "regular_price_naira": 20000,
        "price_usd": 15.0,
        "regular_price_usd": 40.0,
        "is_bundle": True,
        "bundle_items_count": 7,
        "target_persona": "University, college, and polytechnic students struggling with low GPA, exam panic, or academic probation.",
        "core_problem": "Studying 10+ hours a day blindly, experiencing brain fog, forgetting 80% of what was read, and failing exams despite high effort.",
        "dream_outcome": "Achieve First-Class or top 5% GPA standing with half the study time through high-yield cognitive retrieval systems.",
        "primary_hook": "You're not lazy — you just don't have the right system yet.",
        "features": [
            "Complete 7-volume digital masterclass suite",
            "High-yield syllabus filtering protocol",
            "30-day daily accountability tracker",
            "Deep work distraction shield template",
            "High-stakes exam survival blueprint",
        ],
        "benefits": [
            "Cut study time by 50% while improving retention",
            "Eliminate exam panic and freeze responses during tests",
            "Turn academic discipline into an automatic daily habit",
        ],
        "cross_sell_slugs": ["balance-academics-and-business", "how-to-close-high-paying-clients-in-the-dms"],
        "url_path": "/#product-academic-comeback-package",
    },
    {
        "slug": "get-good-at-hard-things",
        "title": "Get Good at Hard Things",
        "sku": "BOOK-GET-GOOD-AT-HARD-THINGS",
        "category": "Academic Performance & High GPA",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Students and ambitious learners who struggle to master difficult, complex, or abstract subjects.",
        "core_problem": "Giving up when coursework gets mathematically dense or intellectually challenging; feeling fundamentally 'not smart enough'.",
        "dream_outcome": "Develop intellectual stamina, rapid cognitive deconstruction, and the ability to master any hard subject effortlessly.",
        "primary_hook": "The top student in your class isn't smarter than you. They just have a method for difficult concepts.",
        "features": [
            "Deliberate practice scaffolding architecture",
            "Mental model decomposition for tough formulas and theories",
            "Cognitive load management protocols",
        ],
        "benefits": [
            "Tackle the hardest courses in your curriculum without fear",
            "Retain complex concepts on the first pass",
        ],
        "cross_sell_slugs": ["how-to-score-high-in-any-exam", "result-oriented-learning"],
        "url_path": "/#product-get-good-at-hard-things",
    },
    {
        "slug": "how-to-score-high-in-any-exam",
        "title": "How to Score High in Any Exam",
        "sku": "BOOK-HOW-TO-SCORE-HIGH-IN-ANY-EXAM",
        "category": "Academic Performance & High GPA",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Students preparing for semester finals, professional certifications, or high-stakes standardized tests.",
        "core_problem": "Exam room blank-outs, poor question timing, and studying the wrong topics that never appear on the test paper.",
        "dream_outcome": "Walk into any examination hall completely prepared, accurately predicting 80% of test questions, and finishing with top marks.",
        "primary_hook": "Exam anxiety has nothing to do with the exam. It is an information retrieval deficit.",
        "features": [
            "Past question reverse-engineering framework",
            "Active recall testing triggers",
            "48-hour pre-exam tactical review schedule",
        ],
        "benefits": [
            "Predict test patterns before entering the hall",
            "Answer exam questions in the exact format examiners award marks for",
        ],
        "cross_sell_slugs": ["result-oriented-learning", "30-day-study-tracker"],
        "url_path": "/#product-how-to-score-high-in-any-exam",
    },
    {
        "slug": "balance-academics-and-business",
        "title": "How to Balance Your Academics and Your Business",
        "sku": "BOOK-BALANCE-ACADEMICS-AND-BUSINESS",
        "category": "Academic Performance & High GPA",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Student entrepreneurs, campus freelancers, and hustle-minded undergraduates running side projects.",
        "core_problem": "Failing courses because client work takes over, or starving the business because school exams demand all attention.",
        "dream_outcome": "Run a profitable campus enterprise or freelance practice while maintaining a solid Second-Class Upper or First-Class GPA.",
        "primary_hook": "You don't have to sacrifice your degree to make money, and you don't have to stay broke to graduate.",
        "features": [
            "Time-blocking and energy allocation matrix",
            "Delegation systems for campus businesses",
            "Exam-month business automation protocol",
        ],
        "benefits": [
            "Build real-world cash flow without dropping out or failing",
            "Eliminate constant guilt of ignoring school or neglecting clients",
        ],
        "cross_sell_slugs": ["how-to-close-high-paying-clients-in-the-dms", "how-to-do-your-ideas"],
        "url_path": "/#product-balance-academics-and-business",
    },
    {
        "slug": "result-oriented-learning",
        "title": "Result-Oriented Learning",
        "sku": "BOOK-RESULT-ORIENTED-LEARNING",
        "category": "Academic Performance & High GPA",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Overworked students studying thick textbooks page-by-page with diminishing returns.",
        "core_problem": "Wasting 70% of study time reading low-yield filler material that never appears in actual assessments.",
        "dream_outcome": "Identify the critical 20% of high-yield concepts that produce 80% of exam marks, mastering syllabi in record time.",
        "primary_hook": "Working hard on the wrong things is worse than not working at all.",
        "features": [
            "High-yield curriculum triage framework",
            "Concept filtering checklists",
            "Exam question mapping methodology",
        ],
        "benefits": [
            "Stop reading massive textbooks blindly from cover to cover",
            "Master essential course concepts in 3 weeks instead of 3 months",
        ],
        "cross_sell_slugs": ["get-good-at-hard-things", "focus-template"],
        "url_path": "/#product-result-oriented-learning",
    },
    {
        "slug": "30-day-study-tracker",
        "title": "30-Day Study Tracker",
        "sku": "BOOK-30-DAY-STUDY-TRACKER",
        "category": "Academic Performance & High GPA",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Students who start every semester with high ambition but lose momentum by week 3.",
        "core_problem": "Procrastination, irregular study schedules, and sudden panic when exam timetables are released.",
        "dream_outcome": "Unbreakable daily study rhythm with visible progress milestones and 100% syllabus coverage before exams start.",
        "primary_hook": "Your grades reflect your daily habits, not your potential.",
        "features": [
            "Visual syllabus coverage tracker",
            "Daily micro-commitment logging",
            "Weekly review and diagnostic check-ins",
        ],
        "benefits": [
            "Never wonder what to study when sitting at your desk",
            "Eliminate cramming panic by completing coursework early",
        ],
        "cross_sell_slugs": ["focus-template", "how-to-score-high-in-any-exam"],
        "url_path": "/#product-30-day-study-tracker",
    },
    {
        "slug": "focus-template",
        "title": "Focus Template: Deep Work Protocol",
        "sku": "BOOK-FOCUS-TEMPLATE",
        "category": "Academic Performance & High GPA",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Anyone struggling with smartphone addiction, social media distraction, and scattered attention.",
        "core_problem": "Picking up your phone every 7 minutes while trying to study or work; taking 4 hours to finish a 45-minute task.",
        "dream_outcome": "Enter distraction-free flow state within 3 minutes and sustain unbroken focus for 90-minute blocks.",
        "primary_hook": "You are not multitasking — you are paying an enormous cognitive switching cost.",
        "features": [
            "Environmental digital distraction elimination checklist",
            "Flow state trigger setup protocols",
            "Post-focus cognitive reset rituals",
        ],
        "benefits": [
            "Double your daily study and work output in half the time",
            "Protect your attention span from digital burnout",
        ],
        "cross_sell_slugs": ["how-to-do-your-ideas", "quitting-the-handjob"],
        "url_path": "/#product-focus-template",
    },
    {
        "slug": "exam-survival-guide",
        "title": "Exam Survival Guide",
        "sku": "BOOK-EXAM-SURVIVAL-GUIDE",
        "category": "Academic Performance & High GPA",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Students facing imminent exams with very little preparation time remaining.",
        "core_problem": "Running out of time before exams; paralyzing anxiety that leads to giving up completely.",
        "dream_outcome": "Triage your remaining 72 hours, prioritize maximum-value topics, and salvage high passing grades under extreme pressure.",
        "primary_hook": "When stakes are highest, tactical preparation beats emotional panic.",
        "features": [
            "Emergency 72-hour revision triage timetable",
            "High-stakes exam morning cognitive priming",
            "Blank-out recovery protocol for the exam hall",
        ],
        "benefits": [
            "Rescue your semester even if you started studying dangerously late",
            "Remain calm and clear-headed under high exam pressure",
        ],
        "cross_sell_slugs": ["how-to-score-high-in-any-exam", "result-oriented-learning"],
        "url_path": "/#product-exam-survival-guide",
    },
    {
        "slug": "how-to-close-high-paying-clients-in-the-dms",
        "title": "How to Close High-Paying Clients in the DMs",
        "sku": "BOOK-HOW-TO-CLOSE-HIGH-PAYING-CLIENTS-IN-THE-DMS",
        "category": "High-Income Skills & Career Power",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Freelancers, designers, copywriters, agency owners, and young corporate professionals looking to monetize skills.",
        "core_problem": "Getting ghosted after quoting prices, sounding pushy or awkward in DMs, and working for low-paying micro-clients.",
        "dream_outcome": "Convert social media direct messages into ₦200,000–₦1,000,000 upfront retainers using respectful conversational frameworks.",
        "primary_hook": "Closing high-paying clients isn't about pushing hard. It is about structured conversation frameworks.",
        "features": [
            "Copy-paste DM opening sequences with 80%+ response rates",
            "The Permission Close objection handling framework",
            "Price presentation scripts that anchor 6-figure value",
        ],
        "benefits": [
            "Land high-paying clients on WhatsApp, Instagram, and LinkedIn without cold calls",
            "Never feel awkward or manipulative discussing money again",
        ],
        "cross_sell_slugs": ["what-to-do-when-your-boss-is-angry-with-you", "how-to-do-your-ideas"],
        "url_path": "/how-to-close-high-paying-clients-in-the-dms.html",
    },
    {
        "slug": "what-to-do-when-your-boss-is-angry-with-you",
        "title": "What To Do When Your Boss Is Angry With You",
        "sku": "BOOK-WHAT-TO-DO-WHEN-YOUR-BOSS-IS-ANGRY-WITH-YOU",
        "category": "High-Income Skills & Career Power",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Employed professionals, corporate climbers, and entry-to-mid-level staff facing tension with management.",
        "core_problem": "Workplace anxiety after making a high-profile mistake, walking on eggshells around a difficult boss, fear of being fired.",
        "dream_outcome": "De-escalate managerial rage, rebuild executive trust, protect your employment, and turn workplace conflict into career leverage.",
        "primary_hook": "A workplace crisis doesn't have to end your career. Handled correctly, it can become your biggest promotion catalyst.",
        "features": [
            "The 4-step crisis meeting formula",
            "Executive apology email templates that project competence rather than weakness",
            "Managerial psychology de-escalation scripts",
        ],
        "benefits": [
            "Walk into your boss's office with confidence and emotional control",
            "Re-establish your reputation as an irreplaceable operator",
        ],
        "cross_sell_slugs": ["how-to-close-high-paying-clients-in-the-dms", "how-to-do-your-ideas"],
        "url_path": "/what-to-do-when-your-boss-is-angry-with-you.html",
    },
    {
        "slug": "quitting-the-handjob",
        "title": "Quitting The Handjob",
        "sku": "BOOK-QUITTING-THE-HANDJOB",
        "category": "Personal Mastery & Mental Freedom",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Men and young adults struggling with compulsive pornography use, masturbation addiction, and brain fog.",
        "core_problem": "Loss of drive, shame cycles, depleted dopamine sensitivity, delayed physical and social confidence.",
        "dream_outcome": "Achieve total lasting freedom from pornography and compulsive habits; restore natural energy, mental clarity, and self-respect.",
        "primary_hook": "Addiction isn't a moral failure. It is a neurochemical loop that can be systematically rewired.",
        "features": [
            "The 21-day neurochemical dopamine reset protocol",
            "Environmental cue-elimination architecture",
            "Urge-surfing and cognitive disruption techniques",
        ],
        "benefits": [
            "Clear brain fog and regain razor-sharp focus",
            "Eliminate secret shame and restore unshakeable masculine confidence",
        ],
        "cross_sell_slugs": ["focus-template", "how-to-do-your-ideas"],
        "url_path": "/quitting-the-handjob.html",
    },
    {
        "slug": "what-to-do-after-a-breakup",
        "title": "What to Do After a Breakup",
        "sku": "BOOK-WHAT-TO-DO-AFTER-A-BREAKUP",
        "category": "Personal Mastery & Mental Freedom",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Anyone going through painful romantic heartbreak, separation, or divorce who feels lost and emotionally paralyzed.",
        "core_problem": "Obsessive profile stalking, agonizing regret, inability to eat or sleep, feeling unworthy and devastated.",
        "dream_outcome": "Break emotional addiction to your ex, restore deep self-respect, heal completely, and become genuinely happy without them.",
        "primary_hook": "The suffering of a breakup isn't about the person you lost. It is about the identity you attached to them.",
        "features": [
            "The strict No-Contact execution manual",
            "Neurobiology of romantic withdrawal and urge-surfing",
            "Self-respect and identity reconstruction roadmap",
        ],
        "benefits": [
            "Stop the urge to send desperate text messages or check their social media",
            "Rebuild your life, peace of mind, and attractive self-worth in 30 days",
        ],
        "cross_sell_slugs": ["how-to-do-your-ideas", "get-good-at-hard-things"],
        "url_path": "/what-to-do-after-a-breakup.html",
    },
    {
        "slug": "how-to-do-your-ideas",
        "title": "How to Do Your Ideas",
        "sku": "BOOK-HOW-TO-DO-YOUR-IDEAS",
        "category": "Personal Mastery & Mental Freedom",
        "price_naira": 5000,
        "regular_price_naira": 25000,
        "price_usd": 15.0,
        "is_bundle": False,
        "target_persona": "Creative thinkers, visionaries, and aspiring founders paralyzed by overthinking and perfectionism.",
        "core_problem": "Hundreds of brilliant ideas trapped inside notes apps, never launched because of fear of judgment or perfectionism.",
        "dream_outcome": "Transform inspiration into real-world launched projects, products, or campaigns within 7 days.",
        "primary_hook": "Execution is not a personality trait. It is a systematic process of reducing starting friction.",
        "features": [
            "The Minimum Viable Execution (MVE) sprint model",
            "Perfectionism demolition framework",
            "The 48-hour prototype launch protocol",
        ],
        "benefits": [
            "Ship ideas before self-doubt and analysis paralysis kill them",
            "Build momentum, tangible portfolio assets, and revenue",
        ],
        "cross_sell_slugs": ["how-to-close-high-paying-clients-in-the-dms", "balance-academics-and-business"],
        "url_path": "/how-to-do-your-ideas.html",
    },
]


def get_product_knowledge_base() -> List[Dict[str, Any]]:
    """Returns the single source of truth product knowledge base."""
    return PRODUCT_KNOWLEDGE_BASE


def get_product_by_slug(slug: Optional[str]) -> Optional[Dict[str, Any]]:
    """Look up verified product metadata by slug."""
    if not slug:
        return None
    clean = slug.strip().lower()
    for p in PRODUCT_KNOWLEDGE_BASE:
        if p["slug"] == clean:
            return p
    return None


def recommend_cross_sell_product(purchased_slugs: List[str]) -> Optional[Dict[str, Any]]:
    """
    Intelligently recommends the next highest-affinity unpurchased book
    based on customer's purchase history.
    Never recommends an already-owned book.
    """
    purchased_set = set(str(s).strip().lower() for s in purchased_slugs if s)

    # 1. Academic Comeback Package / All-access buyers
    # They already own books 1-7. Recommend career & execution masterclasses in order:
    if "all" in purchased_set or "academic-comeback-package" in purchased_set:
        priority_cross_sells = [
            "how-to-close-high-paying-clients-in-the-dms",
            "what-to-do-when-your-boss-is-angry-with-you",
            "how-to-do-your-ideas",
            "quitting-the-handjob",
            "what-to-do-after-a-breakup",
        ]
        for candidate in priority_cross_sells:
            if candidate not in purchased_set:
                return get_product_by_slug(candidate)

    # 2. Check purchased products' declared cross_sell_slugs
    for bought in purchased_set:
        prod = get_product_by_slug(bought)
        if prod:
            for next_slug in prod.get("cross_sell_slugs", []):
                if next_slug not in purchased_set:
                    return get_product_by_slug(next_slug)

    # 3. Fallback to any unpurchased standalone canonical product
    for p in PRODUCT_KNOWLEDGE_BASE:
        if p["slug"] not in purchased_set and not p.get("is_bundle"):
            return p

    return None


# ── Audience Segmentation Engine ────────────────────────────────────────────

SEGMENT_DEFINITIONS = [
    {
        "key": "all_consented",
        "name": "All Active Consented Audience",
        "description": "Every verified subscriber with active marketing consent, excluding unsubscribes.",
    },
    {
        "key": "buyers_all",
        "name": "All Paying Customers (LTV Expansion)",
        "description": "Verified buyers who have completed at least one purchase on the platform.",
    },
    {
        "key": "buyers_academic",
        "name": "Academic Buyers (Cross-Sell to Career & Personal)",
        "description": "Customers who purchased the Academic Comeback Package or academic study guides.",
    },
    {
        "key": "buyers_career",
        "name": "Career & High-Income Buyers",
        "description": "Customers who purchased DM sales, Boss conflict, or Business guides.",
    },
    {
        "key": "buyers_personal",
        "name": "Personal Mastery & Wellness Buyers",
        "description": "Customers who purchased Quitting The Handjob, Breakup, or Execution guides.",
    },
    {
        "key": "unconverted_leads",
        "name": "Unconverted Checkout Leads",
        "description": "High-intent visitors who entered checkout details but did not complete payment.",
    },
    {
        "key": "community_free",
        "name": "Free Community Members",
        "description": "Subscribers who opted in via WhatsApp community forms but have not purchased yet.",
    },
    {
        "key": "dormant_buyers",
        "name": "Dormant Customers (Win-Back)",
        "description": "Paying customers whose last purchase was more than 45 days ago.",
    },
]


async def get_suppression_set(db) -> set:
    """Returns set of all unsubscribed or suppressed email addresses."""
    suppressed = set()
    if db is None:
        return suppressed

    # 1. Unsubscribed subscribers
    cursor = db.subscribers.find({"is_active": False}, {"email": 1})
    async for doc in cursor:
        if doc.get("email"):
            suppressed.add(doc["email"].strip().lower())

    # 2. Recovery unsubscribes
    if "recovery_unsubscribes" in await db.list_collection_names():
        cursor2 = db.recovery_unsubscribes.find({}, {"email": 1})
        async for doc in cursor2:
            if doc.get("email"):
                suppressed.add(doc["email"].strip().lower())

    return suppressed


async def get_segment_recipients(db, segment_key: str) -> List[Dict[str, Any]]:
    """
    Evaluates and returns the clean, deduplicated, consented recipient list for a segment.
    Strictly filters against suppression and unverified emails.
    """
    if db is None:
        return []

    suppressed = await get_suppression_set(db)
    recipients = []
    seen = set()

    now = datetime.now(timezone.utc)
    dormant_cutoff = now - timedelta(days=45)

    if segment_key == "all_consented":
        cursor = db.subscribers.find({"is_active": True})
        async for sub in cursor:
            email = (sub.get("email") or "").strip().lower()
            if email and EMAIL_REGEX.match(email) and email not in suppressed and email not in seen:
                seen.add(email)
                recipients.append({
                    "email": email,
                    "name": sub.get("name") or "Valued Member",
                    "unsubscribe_token": sub.get("unsubscribe_token") or "",
                    "subscriber_id": sub.get("_id"),
                })

    elif segment_key == "buyers_all":
        # Pull from payments with status success
        cursor = db.payments.find({"status": "success"})
        async for p in cursor:
            email = (p.get("email") or "").strip().lower()
            if email and EMAIL_REGEX.match(email) and email not in suppressed and email not in seen:
                seen.add(email)
                sub = await db.subscribers.find_one({"email": email})
                recipients.append({
                    "email": email,
                    "name": p.get("name") or (sub.get("name") if sub else "Valued Customer"),
                    "unsubscribe_token": sub.get("unsubscribe_token", "") if sub else "",
                    "user_id": p.get("user_id"),
                })

    elif segment_key == "buyers_academic":
        academic_skus = ["ACP-BUNDLE", "BOOK-GET-GOOD-AT-HARD-THINGS", "BOOK-HOW-TO-SCORE-HIGH-IN-ANY-EXAM",
                         "BOOK-RESULT-ORIENTED-LEARNING", "BOOK-30-DAY-STUDY-TRACKER", "BOOK-FOCUS-TEMPLATE",
                         "BOOK-EXAM-SURVIVAL-GUIDE", "BOOK-BALANCE-ACADEMICS-AND-BUSINESS"]
        cursor = db.payments.find({
            "status": "success",
            "$or": [
                {"product_sku": {"$in": academic_skus}},
                {"product_slug": {"$in": [s.lower().replace("book-", "") for s in academic_skus]}},
                {"product_name": {"$regex": "academic|exam|study|focus|result", "$options": "i"}},
            ]
        })
        async for p in cursor:
            email = (p.get("email") or "").strip().lower()
            if email and EMAIL_REGEX.match(email) and email not in suppressed and email not in seen:
                seen.add(email)
                sub = await db.subscribers.find_one({"email": email})
                recipients.append({
                    "email": email,
                    "name": p.get("name") or (sub.get("name") if sub else "Scholar"),
                    "unsubscribe_token": sub.get("unsubscribe_token", "") if sub else "",
                    "user_id": p.get("user_id"),
                })

    elif segment_key == "buyers_career":
        career_slugs = ["how-to-close-high-paying-clients-in-the-dms", "what-to-do-when-your-boss-is-angry-with-you", "balance-academics-and-business"]
        cursor = db.payments.find({
            "status": "success",
            "$or": [
                {"product_slug": {"$in": career_slugs}},
                {"product_name": {"$regex": "client|boss|business|dm", "$options": "i"}},
            ]
        })
        async for p in cursor:
            email = (p.get("email") or "").strip().lower()
            if email and EMAIL_REGEX.match(email) and email not in suppressed and email not in seen:
                seen.add(email)
                sub = await db.subscribers.find_one({"email": email})
                recipients.append({
                    "email": email,
                    "name": p.get("name") or (sub.get("name") if sub else "Leader"),
                    "unsubscribe_token": sub.get("unsubscribe_token", "") if sub else "",
                    "user_id": p.get("user_id"),
                })

    elif segment_key == "buyers_personal":
        personal_slugs = ["quitting-the-handjob", "what-to-do-after-a-breakup", "how-to-do-your-ideas"]
        cursor = db.payments.find({
            "status": "success",
            "$or": [
                {"product_slug": {"$in": personal_slugs}},
                {"product_name": {"$regex": "quitting|breakup|ideas|handjob", "$options": "i"}},
            ]
        })
        async for p in cursor:
            email = (p.get("email") or "").strip().lower()
            if email and EMAIL_REGEX.match(email) and email not in suppressed and email not in seen:
                seen.add(email)
                sub = await db.subscribers.find_one({"email": email})
                recipients.append({
                    "email": email,
                    "name": p.get("name") or (sub.get("name") if sub else "Friend"),
                    "unsubscribe_token": sub.get("unsubscribe_token", "") if sub else "",
                    "user_id": p.get("user_id"),
                })

    elif segment_key == "unconverted_leads":
        # Find leads who haven't completed payment
        cursor = db.leads.find({"converted": False})
        async for lead in cursor:
            email = (lead.get("email") or "").strip().lower()
            if email and EMAIL_REGEX.match(email) and email not in suppressed and email not in seen:
                # Double check they didn't pay under another record
                paid = await db.payments.find_one({"email": email, "status": "success"})
                if not paid:
                    seen.add(email)
                    sub = await db.subscribers.find_one({"email": email})
                    recipients.append({
                        "email": email,
                        "name": lead.get("name") or (sub.get("name") if sub else "Friend"),
                        "unsubscribe_token": sub.get("unsubscribe_token", "") if sub else "",
                    })

    elif segment_key == "community_free":
        cursor = db.subscribers.find({"tags": "community", "is_active": True})
        async for sub in cursor:
            email = (sub.get("email") or "").strip().lower()
            if email and EMAIL_REGEX.match(email) and email not in suppressed and email not in seen:
                paid = await db.payments.find_one({"email": email, "status": "success"})
                if not paid:
                    seen.add(email)
                    recipients.append({
                        "email": email,
                        "name": sub.get("name") or "Community Member",
                        "unsubscribe_token": sub.get("unsubscribe_token") or "",
                        "subscriber_id": sub.get("_id"),
                    })

    elif segment_key == "dormant_buyers":
        # Find buyers who have not purchased in > 45 days
        cursor = db.payments.find({"status": "success", "created_at": {"$lte": dormant_cutoff}})
        async for p in cursor:
            email = (p.get("email") or "").strip().lower()
            if email and EMAIL_REGEX.match(email) and email not in suppressed and email not in seen:
                recent = await db.payments.find_one({"email": email, "status": "success", "created_at": {"$gt": dormant_cutoff}})
                if not recent:
                    seen.add(email)
                    sub = await db.subscribers.find_one({"email": email})
                    recipients.append({
                        "email": email,
                        "name": p.get("name") or (sub.get("name") if sub else "Valued Customer"),
                        "unsubscribe_token": sub.get("unsubscribe_token", "") if sub else "",
                        "user_id": p.get("user_id"),
                    })

    return recipients


async def get_audience_segments(db) -> List[Dict[str, Any]]:
    """Returns all available audience segments with live counts of eligible recipients."""
    results = []
    for s in SEGMENT_DEFINITIONS:
        recipients = await get_segment_recipients(db, s["key"])
        results.append({
            "key": s["key"],
            "name": s["name"],
            "description": s["description"],
            "eligible_count": len(recipients),
        })
    return results


# ── Direct-Response AI Copy Generator ───────────────────────────────────────

def generate_ai_campaign_copy(
    product_slug: str,
    campaign_type: str = "direct_response",
    target_segment: str = "all_consented",
) -> Dict[str, Any]:
    """
    Synthesizes high-converting email copy grounded strictly in the verified
    Product Knowledge Base. Employs direct response frameworks from Hormozi, Suby,
    and Kennedy without fabricating facts or hallucinating pricing.
    """
    prod = get_product_by_slug(product_slug) or PRODUCT_KNOWLEDGE_BASE[0]
    app_url = settings.APP_URL.rstrip("/")
    prod_url = f"{app_url}{prod.get('url_path', '/')}"
    price_naira = int(prod.get("price_naira", 5000))
    regular_naira = int(prod.get("regular_price_naira", 25000))
    formatted_price = f"₦{price_naira:,}"
    formatted_regular = f"₦{regular_naira:,}"

    title = prod["title"]
    hook = prod["primary_hook"]
    core_problem = prod["core_problem"]
    dream_outcome = prod["dream_outcome"]
    persona = prod["target_persona"]
    features = prod.get("features", [])

    features_html = "".join([f'<li style="margin-bottom: 8px; color: #cbd5e1;"><strong>{f}</strong></li>' for f in features])
    features_text = "\n".join([f"- {f}" for f in features])

    # 1. Direct Response Offer (Friday Cadence)
    if campaign_type == "direct_response":
        subject_options = [
            f"Why {core_problem.split(';')[0].lower()} (and how to fix it tonight)",
            f"{hook} (Read this before tonight)",
            f"The tactical system to {dream_outcome.split('with')[0].lower()}",
        ]
        preheader = f"Download {title} to your phone for {formatted_price} (Regular: {formatted_regular})."

        html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject_options[0]}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0; -webkit-font-smoothing: antialiased;">
  <!-- Preheader -->
  <div style="display: none; max-height: 0px; overflow: hidden; font-size: 1px; line-height: 1px; color: #0b0f19; opacity: 0;">
    {preheader}
  </div>

  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #0b0f19; padding: 24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; background-color: #131b2e; border-radius: 12px; border: 1px solid rgba(212, 175, 55, 0.25); overflow: hidden; box-shadow: 0 12px 36px rgba(0,0,0,0.6);">
          
          <!-- Header -->
          <tr>
            <td align="center" style="padding: 24px 20px; background: linear-gradient(180deg, #1e293b 0%, #131b2e 100%); border-bottom: 2px solid #d4af37;">
              <span style="font-size: 20px; font-weight: 800; letter-spacing: 2px; color: #f3e5ab; text-transform: uppercase;">SCALE GROUP</span>
              <p style="margin: 4px 0 0 0; font-size: 11px; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase;">Digital Masterclasses & Tactical Systems</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 28px 24px; font-size: 15px; line-height: 1.65; color: #cbd5e1;">
              <p style="margin-top: 0; font-size: 16px; font-weight: 600; color: #ffffff;">Hello {{{{ name }}}},</p>

              <div style="background-color: #1e293b; border-left: 4px solid #d4af37; padding: 16px 20px; border-radius: 0 8px 8px 0; margin: 20px 0;">
                <p style="margin: 0; font-size: 16px; font-weight: 700; color: #f3e5ab; line-height: 1.4;">
                  "{hook}"
                </p>
              </div>

              <p>Most people experiencing <strong>{core_problem}</strong> believe the problem is personal motivation, talent, or luck.</p>

              <p>It isn't.</p>

              <p>When high performers achieve <strong>{dream_outcome}</strong>, they are not relying on sheer willpower. They are using a reliable, repeatable architecture.</p>

              <p>That is why we published <strong>{title}</strong>.</p>

              <!-- Deliverable Box -->
              <div style="background-color: #0f172a; border: 1px solid rgba(212, 175, 55, 0.3); border-radius: 8px; padding: 20px; margin: 24px 0;">
                <span style="display: inline-block; background-color: rgba(212, 175, 55, 0.15); color: #f3e5ab; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; margin-bottom: 8px;">Instant Digital PDF Manual</span>
                <h3 style="margin: 4px 0 12px 0; color: #ffffff; font-size: 18px;">{title}</h3>
                
                <ul style="margin: 0; padding-left: 20px;">
                  {features_html}
                </ul>

                <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; align-items: baseline;">
                  <span style="font-size: 22px; font-weight: 800; color: #d4af37;">{formatted_price}</span>
                  <span style="margin-left: 10px; font-size: 14px; color: #64748b; text-decoration: line-through;">{formatted_regular}</span>
                </div>
              </div>

              <!-- Button CTA -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 28px 0;">
                <tr>
                  <td align="center">
                    <a href="{prod_url}" style="display: inline-block; background: linear-gradient(135deg, #d4af37, #f3e5ab); color: #0b0f19; font-weight: 800; font-size: 15px; padding: 14px 32px; border-radius: 50px; text-decoration: none; box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4); text-transform: uppercase; letter-spacing: 0.5px;">
                      Download {title} Now ({formatted_price}) &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <p style="font-size: 13px; color: #94a3b8; text-align: center; margin-top: 10px;">
                📖 Instant access on your phone, laptop, or tablet. Read it in your private customer library immediately after checkout.
              </p>

              <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 24px 0;">

              <p style="margin-bottom: 0; color: #94a3b8; font-size: 14px;">
                <strong>P.S.</strong> The difference between struggling with this problem for another 6 months and fixing it tonight comes down to deciding to use a proven system. Get your copy now before your schedule fills up.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 24px; background-color: #0b0f19; border-top: 1px solid rgba(255,255,255,0.06); font-size: 12px; color: #64748b; line-height: 1.5; text-align: center;">
              <p style="margin: 0 0 8px 0;">Scale Group Digital Publishing &bull; 8 The Scale Conference Blvd, Victoria Island, Lagos, Nigeria</p>
              <p style="margin: 0;">
                You are receiving this because you subscribed or purchased from our educational portal.
                <br>
                <a href="{{{{ app_url }}}}/unsubscribe?token={{{{ unsubscribe_token }}}}" style="color: #d4af37; text-decoration: underline;">1-Click Unsubscribe</a> |
                <a href="{app_url}/library" style="color: #94a3b8; text-decoration: underline;">Your Private Library</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

        plain_text = f"""
Hello {{{{ name }}}},

"{hook}"

Most people experiencing {core_problem} believe the problem is personal motivation, talent, or luck.

It isn't.

When high performers achieve {dream_outcome}, they are using a reliable, repeatable architecture.

That is why we published {title}.

What's inside:
{features_text}

Price: {formatted_price} (Regular retail: {formatted_regular})
Instant digital PDF manual on your phone, tablet, or PC.

Download your copy here:
{prod_url}

P.S. The difference between struggling with this problem for another 6 months and fixing it tonight comes down to having the right manual.

--
Scale Group Digital Publishing
Victoria Island, Lagos, Nigeria
To unsubscribe from marketing updates: {{{{ app_url }}}}/unsubscribe?token={{{{ unsubscribe_token }}}}
"""

    # 2. Educational Masterclass / HVCO (Tuesday Cadence)
    elif campaign_type == "educational_value":
        subject_options = [
            f"The single mistake that makes {core_problem.split(';')[0].lower()}",
            f"How the best performers {dream_outcome.split('with')[0].lower()}",
            f"Before you try to fix this: read this mental model first",
        ]
        preheader = f"High-Value Educational Breakdown: {hook}"

        html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject_options[0]}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0; -webkit-font-smoothing: antialiased;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #0b0f19; padding: 24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; background-color: #131b2e; border-radius: 12px; border: 1px solid rgba(212, 175, 55, 0.25); overflow: hidden;">
          <tr>
            <td align="center" style="padding: 24px 20px; background: linear-gradient(180deg, #1e293b 0%, #131b2e 100%); border-bottom: 2px solid #d4af37;">
              <span style="font-size: 20px; font-weight: 800; letter-spacing: 2px; color: #f3e5ab; text-transform: uppercase;">SCALE GROUP</span>
              <p style="margin: 4px 0 0 0; font-size: 11px; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase;">Tuesday Mindset & Execution Masterclass</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 28px 24px; font-size: 15px; line-height: 1.7; color: #cbd5e1;">
              <p style="margin-top: 0; font-size: 16px; font-weight: 600; color: #ffffff;">Hello {{{{ name }}}},</p>

              <p>There is a specific pattern that separates people who succeed from those who stay stuck in cycles of effort without results:</p>

              <blockquote style="margin: 20px 0; padding: 12px 18px; border-left: 4px solid #d4af37; background: #1e293b; color: #f3e5ab; font-weight: 600; font-style: italic;">
                "{hook}"
              </blockquote>

              <p>Here is what happens when you attempt to solve {core_problem}:</p>
              
              <p>You try harder. You increase effort. You spend more hours grinding. But because the underlying system is flawed, more effort simply produces more exhaustion.</p>

              <p><strong>The Strategic Shift:</strong></p>
              <p>To achieve {dream_outcome}, you must stop focusing on motivation and start designing your environment and process around high-yield leverage.</p>

              <p>Take 15 minutes today to audit your current routine. Where are you applying high effort to low-yield tasks?</p>

              <div style="background-color: #0f172a; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 16px 20px; margin: 24px 0;">
                <p style="margin: 0; font-size: 14px; color: #cbd5e1;">
                  💡 <em>If you want the complete step-by-step system, we mapped out every single protocol in <strong>{title}</strong> ({formatted_price}).</em>
                  <br><br>
                  <a href="{prod_url}" style="color: #d4af37; font-weight: 700; text-decoration: underline;">Read the full overview &rarr;</a>
                </p>
              </div>

              <p style="margin-bottom: 0;">To your continued growth,<br><strong style="color: #ffffff;">David Itoya & The Scale Group Team</strong></p>
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 24px; background-color: #0b0f19; border-top: 1px solid rgba(255,255,255,0.06); font-size: 12px; color: #64748b; line-height: 1.5; text-align: center;">
              <p style="margin: 0;">
                <a href="{{{{ app_url }}}}/unsubscribe?token={{{{ unsubscribe_token }}}}" style="color: #d4af37;">1-Click Unsubscribe</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        plain_text = f"""
Hello {{{{ name }}}},

There is a specific pattern that separates people who succeed from those who stay stuck:

"{hook}"

Here is what happens when you attempt to solve {core_problem}:
You try harder. You increase effort. But because the underlying system is flawed, more effort simply produces more exhaustion.

To achieve {dream_outcome}, stop relying on motivation and start designing your process around high-yield leverage.

Take 15 minutes today to audit your routine.

If you want the complete step-by-step system, read {title} ({formatted_price}):
{prod_url}

To your continued growth,
David Itoya & The Scale Group Team

Unsubscribe: {{{{ app_url }}}}/unsubscribe?token={{{{ unsubscribe_token }}}}
"""

    # 3. Post-Purchase Ascension / Cross-Sell
    else:
        subject_options = [
            f"Now that you have your foundation: here is your next level",
            f"The natural next step after {title}",
            f"Ready to unlock your next breakthrough, {{{{ name }}}}?",
        ]
        preheader = f"Special customer cross-sell recommendation: {title} ({formatted_price})."

        html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject_options[0]}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #0b0f19; padding: 24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; background-color: #131b2e; border-radius: 12px; border: 1px solid rgba(212, 175, 55, 0.25); overflow: hidden;">
          <tr>
            <td align="center" style="padding: 24px 20px; background: linear-gradient(180deg, #1e293b 0%, #131b2e 100%); border-bottom: 2px solid #d4af37;">
              <span style="font-size: 20px; font-weight: 800; letter-spacing: 2px; color: #f3e5ab; text-transform: uppercase;">SCALE GROUP</span>
              <p style="margin: 4px 0 0 0; font-size: 11px; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase;">Exclusive Customer Ascension Recommendation</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 28px 24px; font-size: 15px; line-height: 1.65; color: #cbd5e1;">
              <p style="margin-top: 0; font-size: 16px; font-weight: 600; color: #ffffff;">Hello {{{{ name }}}},</p>

              <p>As a verified member of our student and reader community, you have already taken a major step toward transforming your results.</p>

              <p>Once your initial foundation is set, the next challenge most people encounter is: <strong>{core_problem}</strong>.</p>

              <p>To help you conquer this plateau, we recommend reading <strong>{title}</strong>.</p>

              <div style="background-color: #0f172a; border-left: 4px solid #d4af37; padding: 18px; border-radius: 0 8px 8px 0; margin: 20px 0;">
                <p style="margin: 0; font-weight: 700; color: #f3e5ab; font-size: 15px;">What you will master:</p>
                <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                  {features_html}
                </ul>
              </div>

              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0;">
                <tr>
                  <td align="center">
                    <a href="{prod_url}" style="display: inline-block; background: linear-gradient(135deg, #d4af37, #f3e5ab); color: #0b0f19; font-weight: 800; font-size: 15px; padding: 14px 32px; border-radius: 50px; text-decoration: none;">
                      Add {title} to Your Library ({formatted_price}) &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin-bottom: 0;">Stay focused and keep executing,<br><strong style="color: #ffffff;">David Itoya</strong></p>
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 24px; background-color: #0b0f19; border-top: 1px solid rgba(255,255,255,0.06); font-size: 12px; color: #64748b; line-height: 1.5; text-align: center;">
              <a href="{{{{ app_url }}}}/unsubscribe?token={{{{ unsubscribe_token }}}}" style="color: #d4af37;">1-Click Unsubscribe</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        plain_text = f"""
Hello {{{{ name }}}},

As a verified customer, you have already taken a major step toward transforming your results.

The next challenge you will likely face is: {core_problem}.

To help you conquer this, we recommend {title}:
{features_text}

Get your copy for {formatted_price}:
{prod_url}

Stay focused and keep executing,
David Itoya

Unsubscribe: {{{{ app_url }}}}/unsubscribe?token={{{{ unsubscribe_token }}}}
"""

    return {
        "product_slug": prod["slug"],
        "product_title": prod["title"],
        "price_naira": price_naira,
        "formatted_price": formatted_price,
        "campaign_type": campaign_type,
        "subject_options": subject_options,
        "recommended_subject": subject_options[0],
        "preview_text": preheader,
        "html_body": html_body,
        "plain_text": plain_text,
    }


# ── Campaign Creation & Queue Dispatch ──────────────────────────────────────

async def create_campaign(
    db,
    *,
    title: str,
    product_slug: str,
    target_segment: str,
    subject: str,
    preview_text: str,
    html_body: str,
    plain_text: Optional[str] = None,
    scheduled_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Saves a new marketing campaign draft or scheduled campaign."""
    now = datetime.now(timezone.utc)
    campaign_id = f"CAMP-{secrets.token_hex(4).upper()}"
    plain_content = plain_text or html_to_text(html_body)

    prod = get_product_by_slug(product_slug)
    product_name = prod["title"] if prod else "Scale Masterclass"

    doc = {
        "campaign_id": campaign_id,
        "title": title,
        "product_slug": product_slug,
        "product_name": product_name,
        "target_segment": target_segment,
        "subject": subject,
        "preview_text": preview_text,
        "html_body": html_body,
        "plain_text": plain_content,
        "status": "scheduled" if scheduled_at and scheduled_at > now else "draft",
        "scheduled_at": scheduled_at or now,
        "created_at": now,
        "updated_at": now,
        "sent_at": None,
        "recipients_count": 0,
        "delivered_count": 0,
        "failed_count": 0,
        "revenue_attributed": 0.0,
    }

    if db is not None:
        await db.marketing_campaigns.insert_one(doc)

    return doc


async def send_test_campaign_email(
    db,
    campaign_id: str,
    test_email: str,
) -> Tuple[bool, Optional[str]]:
    """Sends immediate test preview email to specified address."""
    test_email_clean = test_email.strip().lower()
    if not EMAIL_REGEX.match(test_email_clean):
        return (False, "Invalid recipient email address.")

    camp = None
    if db is not None:
        camp = await db.marketing_campaigns.find_one({"campaign_id": campaign_id})

    if not camp:
        return (False, "Campaign not found.")

    subject = f"[TEST] {camp['subject']}"
    # Replace test template tokens
    rendered_html = (
        camp["html_body"]
        .replace("{{ name }}", "Test Reader")
        .replace("{{ app_url }}", settings.APP_URL)
        .replace("{{ unsubscribe_token }}", "test_preview_token")
    )

    success, err = await send_email(test_email_clean, subject, rendered_html)
    return (success, err)


async def launch_campaign(db, campaign_id: str) -> Dict[str, Any]:
    """
    Launches a campaign: resolves target segment, checks suppression,
    enqueues into db.email_queue with kind='marketing', and triggers scheduler.
    """
    if db is None:
        return {"success": False, "error": "Database not connected."}

    camp = await db.marketing_campaigns.find_one({"campaign_id": campaign_id})
    if not camp:
        return {"success": False, "error": "Campaign not found."}

    if camp.get("status") in ("sending", "sent"):
        return {"success": False, "error": "Campaign has already been launched."}

    now = datetime.now(timezone.utc)
    target_segment = camp.get("target_segment", "all_consented")
    recipients = await get_segment_recipients(db, target_segment)

    if not recipients:
        return {"success": False, "error": f"No active consented recipients found in segment '{target_segment}'."}

    # Atomically mark as sending
    await db.marketing_campaigns.update_one(
        {"campaign_id": campaign_id},
        {"$set": {
            "status": "sending",
            "launched_at": now,
            "recipients_count": len(recipients),
        }}
    )

    # Batch enqueue into email_queue
    queue_docs = []
    log_docs = []

    for r in recipients:
        email = r["email"]
        name = r["name"]
        unsub_token = r.get("unsubscribe_token") or ""

        # Pre-render personalized tokens
        custom_html = (
            camp["html_body"]
            .replace("{{ name }}", html.escape(name))
            .replace("{{ app_url }}", settings.APP_URL)
            .replace("{{ unsubscribe_token }}", unsub_token)
        )

        queue_docs.append({
            "kind": "marketing",
            "campaign_id": campaign_id,
            "email": email,
            "name": name,
            "subject": camp["subject"],
            "html_body": custom_html,
            "plain_text": camp.get("plain_text", ""),
            "unsubscribe_token": unsub_token,
            "scheduled_at": now,
            "status": "pending",
            "retry_count": 0,
            "created_at": now,
            "sent_at": None,
            "error": None,
        })

        log_docs.append({
            "campaign_id": campaign_id,
            "email": email,
            "name": name,
            "status": "queued",
            "queued_at": now,
            "sent_at": None,
            "error": None,
        })

    if queue_docs:
        await db.email_queue.insert_many(queue_docs)
    if log_docs:
        await db.marketing_logs.insert_many(log_docs)

    await db.marketing_campaigns.update_one(
        {"campaign_id": campaign_id},
        {"$set": {"status": "sent", "sent_at": now}}
    )

    # Trigger scheduler asynchronously
    from ..workers.email_scheduler import process_email_queue
    import asyncio
    asyncio.create_task(process_email_queue())

    return {
        "success": True,
        "campaign_id": campaign_id,
        "enqueued_count": len(queue_docs),
        "target_segment": target_segment,
    }


# ── Marketing Overview & Performance Metrics ────────────────────────────────

async def get_marketing_overview(db) -> Dict[str, Any]:
    """Returns high-level retention, audience size, and revenue metrics."""
    if db is None:
        return {
            "total_subscribers": 0,
            "total_buyers": 0,
            "active_consented_audience": 0,
            "total_campaigns": 0,
            "campaigns_sent": 0,
            "total_attributed_revenue": 0.0,
            "recent_campaigns": [],
        }

    total_subscribers = await db.subscribers.count_documents({})
    active_consented = await db.subscribers.count_documents({"is_active": True})
    total_buyers = await db.payments.count_documents({"status": "success"})
    total_campaigns = await db.marketing_campaigns.count_documents({})
    campaigns_sent = await db.marketing_campaigns.count_documents({"status": {"$in": ["sent", "sending"]}})

    # Calculate attributed revenue from campaigns
    rev_agg = await db.marketing_campaigns.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$revenue_attributed"}}}
    ]).to_list(1)
    total_rev = rev_agg[0]["total"] if rev_agg else 0.0

    recent_campaigns_cursor = db.marketing_campaigns.find({}, {"_id": 0}).sort("created_at", -1).limit(10)
    recent_campaigns = await recent_campaigns_cursor.to_list(10)

    # Format dates
    for c in recent_campaigns:
        for k in ("created_at", "scheduled_at", "sent_at", "launched_at"):
            if c.get(k) and isinstance(c[k], datetime):
                c[k] = c[k].isoformat()

    return {
        "total_subscribers": total_subscribers,
        "total_buyers": total_buyers,
        "active_consented_audience": active_consented,
        "total_campaigns": total_campaigns,
        "campaigns_sent": campaigns_sent,
        "total_attributed_revenue": total_rev,
        "recent_campaigns": recent_campaigns,
    }
