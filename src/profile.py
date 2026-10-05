from functools import lru_cache
from pathlib import Path

import yaml

PROFILE_PATH = Path(__file__).resolve().parents[1] / "config" / "profile.yaml"


@lru_cache(maxsize=1)
def load_profile() -> dict:

    with PROFILE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        profile = yaml.safe_load(file) or {}
    limits = profile.get("limits", {})
    for key in ("ai_analyses_per_run", "digest_items"):
        if not isinstance(limits.get(key), int) or limits[key] < 0:
            raise ValueError(f"limits.{key} phải là số nguyên không âm.")
    for key in ("min_prefilter_score", "min_store_score", "min_digest_score"):
        if not isinstance(limits.get(key), (int, float)) or not 0 <= limits[key] <= 10:
            raise ValueError(f"limits.{key} phải từ 0 đến 10.")
    return profile
