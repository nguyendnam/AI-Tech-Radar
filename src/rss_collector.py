from datetime import timezone

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


def _clean_html(value: str) -> str:
    if not value:
        return ""
    return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)


def _parse_date(entry) -> str | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if value:
            try:
                dt = date_parser.parse(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except (ValueError, TypeError, OverflowError):
                continue
    return None


def collect_feed(feed_config: dict) -> list[dict]:
    response = requests.get(feed_config["url"], timeout=30)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    items = []

    if getattr(parsed, "bozo", False):
        print(f"[WARN] RSS có cảnh báo: {feed_config['name']}: {parsed.bozo_exception}")

    for entry in parsed.entries[: feed_config.get("max_items", 10)]:
        url = entry.get("link", "").strip()
        title = _clean_html(entry.get("title", "")).strip()
        excerpt = _clean_html(entry.get("summary", "") or entry.get("description", ""))[
            :5000
        ]

        if not url or not title:
            continue

        items.append(
            {
                "url": url,
                "source": feed_config["name"],
                "title": title,
                "raw_excerpt": excerpt,
                "published_at": _parse_date(entry),
            }
        )

    return items
