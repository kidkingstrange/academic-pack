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
}


def resolve_product_pdf_path(product: dict, uploads_dir_setting: str = "uploads/products") -> Optional[Path]:
    """
    Locates the PDF for a product with comprehensive fallbacks across:
    1. pdfs/ directory (the canonical location for updated product files)
    2. uploads_dir (uploads/products/)
    3. Canonical filename aliases and title matching
    """
    raw_path = (product.get("file_path") or "").strip()
    title = (product.get("title") or "").strip().lower()

    candidates: List[str] = [raw_path] if raw_path else []

    for key, aliases in CANONICAL_PRODUCT_MAP.items():
        matched = False
        if raw_path and (key in raw_path.lower() or any(a.lower() in raw_path.lower() for a in aliases)):
            matched = True
        elif key == "get_good" and ("hard things" in title or "get good" in title):
            matched = True
        elif key == "study_tracker" and ("study tracker" in title or "tracker" in title):
            matched = True
        elif key == "balance" and "balance" in title:
            matched = True
        elif key == "exam_pass" and ("pass" in title or "score high" in title or ("exam" in title and "survival" not in title)):
            matched = True
        elif key == "learning" and ("learning" in title or "result" in title):
            matched = True
        elif key == "focus" and "focus" in title:
            matched = True
        elif key == "survival" and "survival" in title:
            matched = True

        if matched:
            candidates.extend(aliases)

    base_dir = Path(__file__).resolve().parent.parent.parent
    uploads_dir = Path(uploads_dir_setting)
    if not uploads_dir.is_absolute():
        uploads_dir = base_dir / uploads_dir_setting
    pdfs_dir = base_dir / "pdfs"

    search_dirs = [pdfs_dir, uploads_dir, Path("pdfs"), Path(uploads_dir_setting)]

    for c in candidates:
        if not c:
            continue
        for d in search_dirs:
            p = d / c
            if p.exists() and p.is_file():
                return p
    return None
