"""Supabase storage shared by every source and job."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache

from supabase import create_client

from src.config import SUPABASE_SECRET_KEY, SUPABASE_URL

TABLE = "radar_items"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@lru_cache(maxsize=1)
def get_client():
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError("Thiếu SUPABASE_URL hoặc SUPABASE_SECRET_KEY.")
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def find_item(candidate):
    rows = (
        get_client()
        .table(TABLE)
        .select("*")
        .eq("url", candidate["url"])
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        rows = (
            get_client()
            .table(TABLE)
            .select("*")
            .eq("source_platform", candidate["source_platform"])
            .eq("external_id", candidate["external_id"])
            .limit(1)
            .execute()
            .data
            or []
        )
    return rows[0] if rows else None


def observe_item(existing, candidate):
    metadata = {**(existing.get("metadata") or {}), **candidate.get("metadata", {})}
    return (
        get_client()
        .table(TABLE)
        .update({"metadata": metadata, "last_seen_at": utc_now()})
        .eq("id", existing["id"])
        .execute()
    )


def save_item(candidate, analysis):
    row = {
        key: candidate.get(key)
        for key in (
            "source_platform",
            "external_id",
            "name",
            "title",
            "description",
            "url",
            "published_at",
            "metadata",
        )
    }
    row.update({key: value for key, value in analysis.items() if key != "relevant"})
    # Duplicate races must not overwrite sent_at, saved or manual status.
    return (
        get_client()
        .table(TABLE)
        .upsert(row, on_conflict="url", ignore_duplicates=True)
        .execute()
    )


def get_unsent_items(min_score=6.5, limit=200):
    return (
        get_client()
        .table(TABLE)
        .select("*")
        .is_("sent_at", "null")
        .gte("final_score", min_score)
        .order("final_score", desc=True)
        .order("discovered_at")
        .limit(limit)
        .execute()
        .data
        or []
    )


def mark_sent(item_id):
    return (
        get_client()
        .table(TABLE)
        .update({"sent_at": utc_now()})
        .eq("id", item_id)
        .execute()
    )


def cleanup_items(min_score, max_score, days):
    if days <= 0:
        raise ValueError("Retention days phải lớn hơn 0.")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    query = (
        get_client()
        .table(TABLE)
        .delete()
        .eq("saved", False)
        .neq("radar_status", "ADOPT")
        .lt("discovered_at", cutoff)
    )
    if min_score is not None:
        query = query.gte("final_score", min_score)
    if max_score is not None:
        query = query.lt("final_score", max_score)
    return len(query.execute().data or [])
