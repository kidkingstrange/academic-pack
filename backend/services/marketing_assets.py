"""
Marketing asset catalog for the affiliate dashboard — deliberately small
("start minimal" per spec): a few existing product-cover banners already
served from /assets/images, plus a couple of ready-made caption
templates pulled from affiliate_resources/docs_markdown's copywriting
guide. Code-defined, not a database collection, since the catalog itself
never changes at runtime — only downloads of it get logged.
"""

MARKETING_ASSETS = [
    {
        "name": "banner_bundle_landscape",
        "type": "banner",
        "label": "Complete Bundle Cover (Landscape)",
        "url": "/assets/images/bookcoverlandscape.webp",
    },
    {
        "name": "banner_cover_1",
        "type": "banner",
        "label": "Book Cover — Study System",
        "url": "/assets/images/bookcover1.webp",
    },
    {
        "name": "banner_cover_2",
        "type": "banner",
        "label": "Book Cover — Exam Mastery",
        "url": "/assets/images/bookcover2.webp",
    },
    {
        "name": "banner_cover_3",
        "type": "banner",
        "label": "Book Cover — Focus & Discipline",
        "url": "/assets/images/bookcover3.webp",
    },
    {
        "name": "caption_whatsapp_status",
        "type": "caption",
        "label": "WhatsApp Status Sequence",
        "text": (
            'Frame 1: "Hate the feeling of reading all night only to stare at an exam paper blankly?"\n\n'
            'Frame 2: "It\'s not your memory. It\'s your study method. Rote memorization fails under exam '
            'stress. Active recall never does."\n\n'
            'Frame 3: "The Academic Comeback Package details the exact step-by-step active recall '
            'blueprint. Grab your bundle now: {link}"'
        ),
    },
    {
        "name": "caption_carryover_angle",
        "type": "caption",
        "label": "Carryover & GPA Rescue Message",
        "text": (
            "Retaking a failed course costs time, tuition, and embarrassment. Preventing a carryover "
            "with a proven study framework is the smartest investment you can make this semester. "
            "Check it out: {link}"
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
