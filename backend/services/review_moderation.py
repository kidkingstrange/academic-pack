"""
Review moderation and spam/profanity filter service.
Implements hybrid auto-approval and notifications.
"""
import re
from typing import Tuple

SPAM_AND_PROFANITY_PATTERNS = [
    r"\b(?:viagra|cialis|crypto|forex|invest|bitcoin|casino|betting|porn|xxx)\b",
    r"https?://(?:(?!\bacademic-comeback\b)[\w\.-]+)+",  # External links
    r"\b(?:scam|fraud|thief|fake|terrible|useless|horrible)\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SPAM_AND_PROFANITY_PATTERNS]


def evaluate_review_moderation(rating: int, text: str) -> Tuple[bool, str]:
    """
    Evaluates review for automatic approval.
    Returns: (approved: bool, reason: str)
    """
    if rating < 1 or rating > 5:
        return False, "invalid_rating"

    clean_text = (text or "").strip()
    if not clean_text:
        return False, "empty_text"

    # Check against keyword patterns
    for pattern in COMPILED_PATTERNS:
        if pattern.search(clean_text):
            return False, "flagged_keyword_or_link"

    # Hybrid auto-approval: 4 and 5 stars pass automatically
    if rating >= 4:
        return True, "auto_approved_high_rating"

    # 1 to 3 stars require manual admin approval
    return False, "pending_manual_review_low_rating"
