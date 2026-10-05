"""Cheap ranking before spending the shared Gemini budget."""

import re

from src.ai import safe_score
from src.profile import load_profile

BASE = {
    "NEWS": 4,
    "PAPER": 4.5,
    "AI_MODEL": 5,
    "DEV_TOOL": 4.5,
    "GITHUB_REPO": 4,
    "LANGUAGE_CANDIDATE": 4,
    "RELEASE": 6,
    "LANGUAGE": 4,
    "FRAMEWORK": 4.5,
    "PACKAGE": 3,
    "SECURITY": 5,
}


def keyword_match(keyword, text):
    return bool(
        re.search(
            r"(?<!\w)" + re.escape(str(keyword).lower()) + r"(?!\w)", text.lower()
        )
    )


def prefilter_score(candidate):
    profile = load_profile()
    text = f"{candidate['title']} {candidate.get('description', '')} {candidate.get('metadata', {})}"
    score = BASE.get(candidate.get("item_type_hint"), 2)
    for name, weight, cap in [
        ("high_priority_keywords", 1.2, 4),
        ("medium_priority_keywords", 0.5, 2),
    ]:
        score += min(
            sum(keyword_match(k, text) for k in profile.get(name, [])) * weight, cap
        )
    metadata = candidate.get("metadata", {})
    for key, thresholds in {
        "stars": [(5000, 2.5), (1000, 2), (100, 1), (20, 0.5)],
        "downloads": [(1000000, 2), (100000, 1.5), (10000, 0.8)],
        "likes": [(1000, 1.2), (100, 0.8), (20, 0.4)],
    }.items():
        try:
            value = float(metadata.get(key) or 0)
        except (ValueError, TypeError):
            value = 0
        score += next(
            (bonus for threshold, bonus in thresholds if value >= threshold), 0
        )
    return safe_score(score)
