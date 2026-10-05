from datetime import datetime, timedelta, timezone

VIETNAM_TZ = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")

TYPE_ICONS = {
    "AI_MODEL": "🧠",
    "DEV_TOOL": "🛠",
    "GITHUB_REPO": "🐙",
    "RELEASE": "🚀",
    "LANGUAGE": "💻",
    "FRAMEWORK": "🧩",
    "PACKAGE": "📦",
    "PAPER": "🔬",
    "SECURITY": "🔐",
    "NEWS": "📰",
    "OTHER": "📡",
}

TYPE_LABELS = {
    "NEWS": "TIN CÔNG NGHỆ",
    "AI_MODEL": "AI MODEL",
    "DEV_TOOL": "DEVELOPER TOOL",
    "GITHUB_REPO": "GITHUB REPOSITORY",
    "RELEASE": "SOFTWARE RELEASE",
    "LANGUAGE": "PROGRAMMING LANGUAGE",
    "FRAMEWORK": "FRAMEWORK / LIBRARY",
    "PACKAGE": "PACKAGE",
    "PAPER": "RESEARCH",
    "SECURITY": "SECURITY",
    "OTHER": "TECH SIGNAL",
}

TYPE_QUOTAS = {
    "NEWS": 4,
    "AI_MODEL": 3,
    "DEV_TOOL": 3,
    "GITHUB_REPO": 4,
    "RELEASE": 4,
    "LANGUAGE": 2,
    "FRAMEWORK": 2,
    "PACKAGE": 2,
    "PAPER": 2,
    "SECURITY": 2,
    "OTHER": 2,
}


def parse_datetime(value):
    """Parse ISO datetime từ Supabase/API."""

    if not value:
        return None

    try:
        value = str(value).strip()
        value = value.replace("Z", "+00:00")

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def publication_label(item_type: str) -> str:
    """Label ngày theo từng loại signal."""

    labels = {
        "NEWS": "Công bố",
        "GITHUB_REPO": "Repo được tạo",
        "RELEASE": "Phát hành",
        "AI_MODEL": "Model xuất hiện",
        "DEV_TOOL": "Tool xuất hiện",
        "LANGUAGE": "Xuất hiện",
        "FRAMEWORK": "Phát hành",
        "PACKAGE": "Package xuất hiện",
        "PAPER": "Công bố",
        "SECURITY": "Công bố",
        "OTHER": "Xuất hiện",
    }

    return labels.get(item_type, "Xuất hiện")


def human_age(published_at: datetime) -> str:
    """
    Chuyển thời gian thành dạng dễ đọc:
    vừa mới xuất hiện, khoảng 5 giờ trước,
    2 ngày trước, khoảng 3 tháng trước...
    """

    now = datetime.now(timezone.utc)

    age = now - published_at.astimezone(timezone.utc)

    total_seconds = max(age.total_seconds(), 0)

    hours = int(total_seconds // 3600)
    days = int(total_seconds // 86400)

    if days == 0:
        if hours <= 0:
            return "vừa mới xuất hiện"

        if hours == 1:
            return "khoảng 1 giờ trước"

        return f"khoảng {hours} giờ trước"

    if days == 1:
        return "1 ngày trước"

    if days < 30:
        return f"{days} ngày trước"

    if days < 365:
        months = max(1, days // 30)
        return f"khoảng {months} tháng trước"

    years = days // 365
    remaining_months = (days % 365) // 30

    if remaining_months > 0:
        return f"khoảng {years} năm {remaining_months} tháng trước"

    return f"khoảng {years} năm trước"


def publication_text(item: dict) -> str:
    """
    Tạo block ngày tháng cho Telegram.

    Ưu tiên published_at.
    Nếu không có thì hiển thị ngày Radar phát hiện.
    """

    item_type = item.get("item_type", "OTHER")

    label = publication_label(item_type)

    published_at = parse_datetime(item.get("published_at"))

    if published_at is None:
        discovered_at = parse_datetime(item.get("discovered_at"))

        if discovered_at is None:
            return f"📅 {label}: Không xác định"

        local_discovered = discovered_at.astimezone(VIETNAM_TZ)

        return (
            f"📅 {label}: Không xác định\n"
            "🔎 Radar phát hiện: "
            f"{local_discovered.strftime('%d/%m/%Y')}"
        )

    local_published = published_at.astimezone(VIETNAM_TZ)

    return (
        f"📅 {label}: "
        f"{local_published.strftime('%d/%m/%Y')}\n"
        "⏳ Xuất hiện: "
        f"{human_age(published_at)}"
    )


def select_balanced(rows: list[dict], total_limit: int) -> list[dict]:
    """
    Chọn signal theo quota từng loại
    để Telegram không bị toàn model
    hoặc toàn GitHub repo.
    """

    if total_limit <= 0:
        return []
    counts = {}
    selected = []

    for row in rows:
        item_type = row.get("item_type", "OTHER")

        quota = TYPE_QUOTAS.get(item_type, 2)

        used = counts.get(item_type, 0)

        if used >= quota:
            continue

        selected.append(row)
        counts[item_type] = used + 1

        if len(selected) >= total_limit:
            break

    return selected


def metadata_text(item: dict) -> str:
    """
    Hiển thị metadata khác nhau
    tùy nguồn và loại công nghệ.
    """

    metadata = item.get("metadata") or {}

    lines = []

    if metadata.get("stars") is not None:
        lines.append(f"⭐ GitHub stars: {metadata['stars']}")

    if metadata.get("language"):
        lines.append(f"💻 Language: {metadata['language']}")

    if metadata.get("license"):
        lines.append(f"📄 License: {metadata['license']}")

    if metadata.get("downloads") is not None:
        lines.append(f"⬇️ Downloads: {metadata['downloads']}")

    if metadata.get("likes") is not None:
        lines.append(f"❤️ Likes: {metadata['likes']}")

    if metadata.get("pipeline_tag"):
        lines.append(f"🧠 Pipeline: {metadata['pipeline_tag']}")

    if metadata.get("tag"):
        lines.append(f"🏷 Version: {metadata['tag']}")

    return "\n".join(lines[:5])


def build_message(item: dict) -> str:
    item_type = item.get("item_type", "OTHER")

    icon = TYPE_ICONS.get(item_type, "📡")

    label = TYPE_LABELS.get(item_type, "TECH SIGNAL")

    score = float(item.get("final_score") or 0)

    publication = publication_text(item)
    metadata = metadata_text(item)

    metadata_block = ""

    if metadata:
        metadata_block = "\n\n" + metadata

    return f"""
{icon} {label}

{item.get("title")}

🎯 Score: {score:.1f}/10
🧭 Radar: {item.get("radar_status", "WATCH")}
🏷 Chủ đề: {item.get("category", "Other")}

{publication}{metadata_block}

📝 NÓ LÀ GÌ?

{item.get("summary") or "Chưa có tóm tắt."}

💡 VÌ SAO ĐÁNG CHÚ Ý?

{item.get("why_it_matters") or "Chưa có phân tích."}

🔗 XEM NGUỒN

{item.get("url")}
""".strip()
