"""
Product PDF Resolution & Delivery Utilities.
Resolves canonical and alias filenames across pdfs/ and uploads/products/.
"""
from pathlib import Path
from typing import Optional, Dict, List

# Mapping from canonical key to all recognized file and title aliases
CANONICAL_PRODUCT_MAP: Dict[str, List[str]] = {
    "get_good": [
        "GET GOOD AT HARD THINGS by David Itoya.pdf",
        "get_good_at_hard_things.pdf",
        "GET_GOOD_AT_HARD_THINGS_by_David_Itoya.pdf",
        "Get_Good_at_Hard_Things.pdf",
    ],
    "study_tracker": [
        "30-Day Study Tracker.pdf",
        "30_day_study_tracker.pdf",
        "30-Day_Study_Tracker.pdf",
    ],
    "balance": [
        "HOW TO BALANCE YOUR ACADEMICS AND YOUR BUSINESS.pdf",
        "balance_academics_and_business.pdf",
        "HOW_TO_BALANCE_YOUR_ACADEMICS_AND_YOUR_BUSINESS.pdf",
        "how_to_balance_academics_and_your_business.pdf",
    ],
    "exam_pass": [
        "HOW TO PASS ANY EXAM WITH HIGH SCORES.pdf",
        "how_to_score_high_in_any_exam.pdf",
        "HOW_TO_PASS_ANY_EXAM_WITH_HIGH_SCORES.pdf",
        "how_to_pass_any_exam_with_high_scores.pdf",
    ],
    "learning": [
        "RESULT-ORIENTED LEARNING.pdf",
        "results_oriented_learning.pdf",
        "result_oriented_learning.pdf",
        "RESULT-ORIENTED_LEARNING.pdf",
        "RESULT_ORIENTED_LEARNING.pdf",
    ],
    "focus": [
        "🎯 Focus Template.pdf",
        "focus_template.pdf",
        "Focus Template.pdf",
        "Focus_Template.pdf",
        "__Focus_Template.pdf",
    ],
    "survival": [
        "🔥 Exam Survival Guide.pdf",
        "exam_survival_guide.pdf",
        "Exam Survival Guide.pdf",
        "Exam_Survival_Guide.pdf",
        "__Exam_Survival_Guide.pdf",
    ],
    "handjob": [
        "Quitting_The_Handjob_David_Itoya.pdf",
        "quitting_the_handjob.pdf",
        "quitting-the-handjob.pdf",
        "Quitting The Handjob.pdf",
    ],
    "dm_clients": [
        "How to Close High-Paying Clients in the DMs - David Itoya.pdf",
        "How to Close High-Paying Clients in the DMs.pdf",
        "how-to-close-high-paying-clients-in-the-dms.pdf",
        "high_paying_clients_in_dm.pdf",
    ],
    "ideas": [
        "How to Do Your Ideas - David Itoya.pdf",
        "How to Do Your Ideas.pdf",
        "how-to-do-your-ideas.pdf",
        "do-your-ideas.pdf",
    ],
    "breakup": [
        "What to Do After a Breakup - David Itoya.pdf",
        "What to Do After a Breakup.pdf",
        "what-to-do-after-a-breakup.pdf",
        "breakup.pdf",
    ],
    "angry_boss": [
        "What To Do When Your Boss Is Angry With You - David Itoya.pdf",
        "What To Do When Your Boss Is Angry With You.pdf",
        "what-to-do-when-your-boss-is-angry-with-you.pdf",
        "how-to-turn-your-boss-into-your-biggest.pdf",
    ],
}


def resolve_product_pdf_path(product: dict, uploads_dir_setting: str = "uploads/products") -> Optional[Path]:
    """
    Locates the PDF for a product with comprehensive fallbacks across:
    1. pdfs/ directory (the canonical location for updated product files)
    2. uploads_dir (uploads/products/)
    3. Canonical filename aliases and title matching
    """
    raw_path = (product.get("file_path") or "").strip()
    title = (product.get("title") or "").strip()
    slug = (product.get("slug") or "").strip()
    title_lower = title.lower()

    candidates: List[str] = [raw_path] if raw_path else []
    if title:
        candidates.append(f"{title}.pdf")
        candidates.append(f"{title} - David Itoya.pdf")
    if slug:
        candidates.append(f"{slug}.pdf")
        candidates.append(f"{slug.replace('-', '_')}.pdf")

    for key, aliases in CANONICAL_PRODUCT_MAP.items():
        matched = False
        if raw_path and (key in raw_path.lower() or any(a.lower() in raw_path.lower() for a in aliases)):
            matched = True
        elif key == "get_good" and ("hard things" in title_lower or "get good" in title_lower):
            matched = True
        elif key == "study_tracker" and ("study tracker" in title_lower or "tracker" in title_lower):
            matched = True
        elif key == "balance" and "balance" in title_lower:
            matched = True
        elif key == "exam_pass" and ("pass" in title_lower or "score high" in title_lower or ("exam" in title_lower and "survival" not in title_lower)):
            matched = True
        elif key == "learning" and ("learning" in title_lower or "result" in title_lower):
            matched = True
        elif key == "focus" and "focus" in title_lower:
            matched = True
        elif key == "survival" and "survival" in title_lower:
            matched = True
        elif key == "handjob" and ("handjob" in title_lower or "quitting" in title_lower or "masturbation" in title_lower or "pornography" in title_lower):
            matched = True
        elif key == "dm_clients" and ("high-paying" in title_lower or "paying client" in title_lower or "dms" in title_lower or "direct message" in title_lower):
            matched = True
        elif key == "ideas" and ("ideas" in title_lower or "do your ideas" in title_lower):
            matched = True
        elif key == "breakup" and ("breakup" in title_lower or "break-up" in title_lower or "ex" in title_lower):
            matched = True
        elif key == "angry_boss" and ("boss" in title_lower or "angry" in title_lower):
            matched = True

        if matched:
            candidates.extend(aliases)

    base_dir = Path(__file__).resolve().parent.parent.parent
    uploads_dir = Path(uploads_dir_setting)
    if not uploads_dir.is_absolute():
        uploads_dir = base_dir / uploads_dir_setting
    pdfs_dir = base_dir / "pdfs"

    search_dirs = [pdfs_dir, uploads_dir, Path("pdfs"), Path(uploads_dir_setting)]

    # 1. Fast direct lookup
    for c in candidates:
        if not c:
            continue
        for d in search_dirs:
            if not d.exists():
                continue
            p = d / c
            if p.exists() and p.is_file():
                return p

    # 2. Recursive subdirectory lookup across pdfs/ and uploads/
    candidate_names = {Path(c).name.lower() for c in candidates if c}
    for d in search_dirs:
        if not d.exists():
            continue
        try:
            for sub_p in d.rglob("*.pdf"):
                if sub_p.is_file():
                    sub_name = sub_p.name.lower()
                    if sub_name in candidate_names:
                        return sub_p
                    if title and title_lower in sub_name:
                        return sub_p
        except Exception:
            continue

    return None
