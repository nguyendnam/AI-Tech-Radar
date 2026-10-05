from datetime import datetime, timezone

import requests

from src.config import MAX_HN_STORIES, TECH_KEYWORDS
from src.scoring import keyword_match

BASE = "https://hacker-news.firebaseio.com/v0"


def _is_relevant(title: str) -> bool:
    t = title.lower()
    return any(keyword_match(keyword, t) for keyword in TECH_KEYWORDS)


def collect_hacker_news() -> list[dict]:
    response = requests.get(f"{BASE}/topstories.json", timeout=20)
    response.raise_for_status()
    ids = response.json()
    items = []

    for item_id in ids[:MAX_HN_STORIES]:
        try:
            response = requests.get(f"{BASE}/item/{item_id}.json", timeout=20)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            print(f"[WARN] HN item {item_id}: {exc}")
            continue

        if not data or data.get("type") != "story":
            continue

        title = (data.get("title") or "").strip()
        if not title or not _is_relevant(title):
            continue

        url = data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
        published_at = datetime.fromtimestamp(
            data.get("time", 0), tz=timezone.utc
        ).isoformat()

        items.append(
            {
                "url": url,
                "source": "Hacker News",
                "title": title,
                "raw_excerpt": (
                    f"Hacker News score={data.get('score', 0)}, "
                    f"comments={data.get('descendants', 0)}, "
                    f"discussion=https://news.ycombinator.com/item?id={item_id}"
                ),
                "published_at": published_at,
            }
        )

    return items
