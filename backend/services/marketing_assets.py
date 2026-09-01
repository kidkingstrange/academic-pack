"""
Marketing asset catalog for the affiliate dashboard — deliberately small
("start minimal" per spec): a few existing product-cover banners already
served from /assets/images, plus ready-made high-converting caption
templates pulled from direct-response copywriting protocols. Code-defined,
not a database collection, since the catalog itself never changes at runtime —
only downloads of it get logged.
"""

MARKETING_ASSETS = [
    {
        "name": "banner_bundle_landscape",
        "type": "banner",
        "label": "Complete Bundle Cover (Landscape)",
        "url": "/assets/images/bookcoverlandscape.webp",
    },
    {
        "name": "banner_cover_get_good",
        "type": "banner",
        "label": "Book Cover — Get Good at Hard Things",
        "url": "/assets/images/bookcover.webp",
    },
    {
        "name": "banner_cover_score_high",
        "type": "banner",
        "label": "Book Cover — How to Score High in Any Exam",
        "url": "/assets/images/bookcover1.webp",
    },
    {
        "name": "banner_cover_balance",
        "type": "banner",
        "label": "Book Cover — How to Balance Academics and Your Business",
        "url": "/assets/images/bookcover2.webp",
    },
    {
        "name": "banner_cover_results_oriented",
        "type": "banner",
        "label": "Book Cover — Results-Oriented Learning System",
        "url": "/assets/images/bookcover3.webp",
    },
    {
        "name": "caption_shawarma_reality_check",
        "type": "caption",
        "label": "WhatsApp Status 1 — The Shawarma vs Carryover Reality Check (Top Converter)",
        "text": (
            "Coursemates who say ₦2k is too much for an exam prep system will happily spend ₦3,500 on "
            "shawarma today and ₦150k on hostel rent next year when they get hit with an avoidable "
            "carryover. Don't be that guy. Grab the package here: {link}"
        ),
    },
    {
        "name": "caption_data_vs_grades",
        "type": "caption",
        "label": "WhatsApp Status 2 — Daily Data vs ₦22/Day GPA Protection",
        "text": (
            "You just spent ₦500 on a 1-day data plan to watch memes. For ₦22 a day, you can install "
            "the exact 20-minute protocol to stop failing 3-unit courses. Grab the early-bird link "
            "before it closes: {link}"
        ),
    },
    {
        "name": "caption_result_portal",
        "type": "caption",
        "label": "WhatsApp Status 3 — Night Class vs Result Portal Reality",
        "text": (
            "The worst feeling in uni isn't failing an exam you didn't read for. It's reading for 6 "
            "hours every night and still seeing a D or C on your result sheet. ₦2,000 fixes your "
            "study technique permanently: {link}"
        ),
    },
    {
        "name": "caption_whatsapp_status_3frame",
        "type": "caption",
        "label": "WhatsApp 3-Frame Story Sequence",
        "text": (
            'Frame 1: "Hate the feeling of reading all night only to stare at an exam paper blankly?"\n\n'
            'Frame 2: "It\'s not your memory. It\'s your study method. Rote memorization fails under exam '
            'stress. Active recall never does."\n\n'
            'Frame 3: "The Academic Comeback Package details the exact step-by-step active recall '
            'blueprint. Grab your bundle now: {link}"'
        ),
    },
]

_BY_NAME = {a["name"]: a for a in MARKETING_ASSETS}


def get_asset(name: str) -> dict:
    return _BY_NAME.get(name)


def list_assets_for_affiliate(referral_link: str) -> list:
    """Return the catalog with each caption's {link} placeholder filled
    in with this affiliate's real referral link. Banners need no
    substitution."""
    out = []
    for asset in MARKETING_ASSETS:
        item = dict(asset)
        if item["type"] == "caption":
            item["text"] = item["text"].format(link=referral_link)
        out.append(item)
    return out
