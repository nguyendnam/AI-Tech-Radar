"""Unified collect, digest and retention jobs."""

import os
from collections import defaultdict, deque
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src import database
from src.ai import (
    AIConfigurationError,
    AnalysisSession,
    PermanentAIError,
    TemporaryAIError,
    analyze_item,
)
from src.collectors.github_discovery import collect_github_repositories
from src.collectors.github_releases import collect_github_releases
from src.collectors.huggingface import collect_huggingface
from src.collectors.pypi import collect_pypi_packages
from src.config import RSS_FEEDS
from src.digest import build_message, select_balanced
from src.hn_collector import collect_hacker_news
from src.profile import load_profile
from src.rss_collector import collect_feed
from src.scoring import prefilter_score
from src.telegram_sender import send_telegram


def canonical_url(url):
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("URL nguồn không hợp lệ.")
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            urlencode(query),
            "",
        )
    )


def normalize_candidate(item):
    candidate = dict(item)
    candidate["url"] = canonical_url(candidate["url"])
    candidate["title"] = str(candidate["title"]).strip()
    if not candidate["title"]:
        raise ValueError("Thiếu title.")
    if "source_platform" not in candidate:
        source = candidate.get("source", "RSS")
        candidate.update(
            source_platform="hn" if source == "Hacker News" else "rss",
            external_id=candidate["url"],
            item_type_hint="PAPER" if "arxiv" in source.lower() else "NEWS",
            metadata={"source": source},
            description=candidate.get("raw_excerpt", ""),
        )
    candidate["metadata"] = candidate.get("metadata") or {}
    candidate["description"] = str(candidate.get("description") or "")[:8000]
    return candidate


def collect_all():
    collectors = [
        (feed["name"], lambda feed=feed: collect_feed(feed)) for feed in RSS_FEEDS
    ]
    collectors += [
        ("Hacker News", collect_hacker_news),
        ("GitHub repos", collect_github_repositories),
        ("GitHub releases", collect_github_releases),
        ("Hugging Face", collect_huggingface),
        ("PyPI", collect_pypi_packages),
    ]
    candidates = []
    for name, collector in collectors:
        try:
            found = collector()
            candidates.extend(found)
            print(f"[COLLECT] {name}: {len(found)}")
        except Exception as exc:
            print(f"[WARN] {name}: {type(exc).__name__}")
    if not candidates:
        raise RuntimeError("Không thu thập được dữ liệu từ bất kỳ nguồn nào.")
    return candidates


def rank_candidates(candidates):
    unique = {}
    identities = set()
    for item in candidates:
        try:
            item = normalize_candidate(item)
            identity = (item["source_platform"], item["external_id"])
            if item["url"] in unique or identity in identities:
                continue
            unique[item["url"]] = item
            identities.add(identity)
        except (KeyError, ValueError, TypeError):
            print("[WARN] Bỏ candidate không hợp lệ.")
    # Round-robin types stops popular models/repos from consuming the news budget.
    groups = defaultdict(deque)
    for item in sorted(unique.values(), key=prefilter_score, reverse=True):
        groups[item["item_type_hint"]].append(item)
    while any(groups.values()):
        for group in groups.values():
            if group:
                yield group.popleft()


def collect():
    limits = load_profile()["limits"]
    analyzed = created = observed = errors = 0
    successful = deferred = 0
    session = AnalysisSession(limit=limits["ai_analyses_per_run"])
    database.get_client()  # Validate storage configuration before collecting.
    for item in rank_candidates(collect_all()):
        try:
            existing = database.find_item(item)
            if existing:
                database.observe_item(existing, item)
                observed += 1
                continue
            if prefilter_score(item) < limits["min_prefilter_score"]:
                continue
            if (
                analyzed >= limits["ai_analyses_per_run"]
                or session.requests >= session.limit
                or session.paused
            ):
                continue  # Still refresh observations of known items.
            analyzed += 1  # Failed requests also consume the budget.
            analysis = analyze_item(item, session=session)
            successful += 1
            if (
                analysis["relevant"]
                and analysis["final_score"] >= limits["min_store_score"]
            ):
                database.save_item(item, analysis)
                created += 1
        except TemporaryAIError as exc:
            deferred += 1
            print(f"[WARN] Deferred {item['title']}: {exc}")
        except AIConfigurationError:
            raise
        except PermanentAIError as exc:
            errors += 1
            print(f"[ERROR] {item['title']}: {exc}")
        except Exception as exc:
            errors += 1
            print(f"[ERROR] {item['title']}: {type(exc).__name__}")
    print(
        f"[DONE] analyzed={analyzed} requests={session.requests} saved={created} "
        f"observed={observed} deferred={deferred} errors={errors}"
    )
    if errors:
        raise RuntimeError(f"Collection có {errors} lỗi; xem log bên trên.")
    if deferred and not successful:
        raise RuntimeError(
            "Gemini tạm thời không xử lý được mục nào; xem warning và thử lại sau."
        )


def digest():
    limits = load_profile()["limits"]
    selected = select_balanced(
        database.get_unsent_items(limits["min_digest_score"]), limits["digest_items"]
    )
    if not selected:
        print("[DONE] Không có nội dung mới đủ điểm.")
        return
    errors = 0
    for item in selected:
        try:
            send_telegram(build_message(item))
            database.mark_sent(item["id"])
        except Exception as exc:
            errors += 1
            print(f"[ERROR] {item['title']}: {type(exc).__name__}")
    print(f"[DONE] sent={len(selected) - errors}/{len(selected)}")
    if errors:
        raise RuntimeError(
            f"Có {errors} nội dung chưa gửi/đánh dấu thành công; lần sau sẽ thử lại."
        )


def cleanup():
    for name, minimum, maximum, default in [
        ("LOW", None, 7, 30),
        ("MEDIUM", 7, 9, 90),
        ("HIGH", 9, None, 365),
    ]:
        days = int(os.getenv(f"RETENTION_{name}_DAYS", str(default)))
        count = database.cleanup_items(minimum, maximum, days)
        print(f"[CLEANUP] {name}: {count}")
