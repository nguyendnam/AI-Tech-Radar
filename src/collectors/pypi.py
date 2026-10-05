from email.utils import parsedate_to_datetime

import feedparser
import requests

from src.profile import load_profile

PYPI_NEWEST = "https://pypi.org/rss/packages.xml"


def normalize_date(value):

    if not value:
        return None

    try:
        return parsedate_to_datetime(value).isoformat()

    except Exception:
        return None


def collect_pypi_packages() -> list[dict]:

    profile = load_profile()

    keywords = [str(keyword).lower() for keyword in profile.get("pypi_keywords", [])]

    limit = int(profile.get("limits", {}).get("pypi_items", 50))

    response = requests.get(PYPI_NEWEST, timeout=30)
    response.raise_for_status()
    feed = feedparser.parse(response.content)

    results = []

    for entry in feed.entries[:limit]:
        title = entry.get("title") or ""

        summary = entry.get("summary") or ""

        haystack = (f"{title} {summary}").lower()

        if not any(keyword in haystack for keyword in keywords):
            continue

        url = entry.get("link") or ""

        results.append(
            {
                "source_platform": "pypi",
                "external_id": url or title,
                "item_type_hint": "PACKAGE",
                "name": title,
                "title": title,
                "description": summary[:3000],
                "url": url,
                "published_at": normalize_date(entry.get("published")),
                "metadata": {"registry": "PyPI"},
            }
        )

    return results
