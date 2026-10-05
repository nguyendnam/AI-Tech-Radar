"""Collect trending Hugging Face models and Spaces with a common item format."""

from huggingface_hub import HfApi

from src.profile import load_profile


def collect_huggingface() -> list[dict]:
    limits = load_profile().get("limits", {})
    api = HfApi()
    results = []
    sources = [
        (
            "model",
            "AI_MODEL",
            api.list_models,
            limits.get("hf_models", 15),
            "downloads",
            "Hugging Face model đang có tín hiệu đáng chú ý.",
        ),
        (
            "space",
            "DEV_TOOL",
            api.list_spaces,
            limits.get("hf_spaces", 10),
            "likes",
            "Hugging Face Space / AI tool đang được chú ý.",
        ),
    ]
    for kind, item_type, list_items, limit, fallback_sort, description in sources:
        try:
            try:
                items = list(list_items(sort="trending_score", limit=int(limit)))
            except Exception:
                items = list(list_items(sort=fallback_sort, limit=int(limit)))

            for item in items:
                created_at = getattr(item, "created_at", None)
                metadata = {
                    "likes": getattr(item, "likes", 0) or 0,
                    "trending_score": getattr(item, "trending_score", 0) or 0,
                    "tags": list(getattr(item, "tags", []) or [])[:30],
                }
                if kind == "model":
                    metadata.update(
                        downloads=getattr(item, "downloads", 0) or 0,
                        pipeline_tag=getattr(item, "pipeline_tag", None),
                    )
                results.append(
                    {
                        "source_platform": "huggingface",
                        "external_id": f"{kind}:{item.id}",
                        "item_type_hint": item_type,
                        "name": item.id,
                        "title": item.id,
                        "description": description,
                        "url": f"https://huggingface.co/{'spaces/' if kind == 'space' else ''}{item.id}",
                        "published_at": created_at.isoformat()
                        if hasattr(created_at, "isoformat")
                        else str(created_at)
                        if created_at is not None
                        else None,
                        "metadata": metadata,
                    }
                )
        except Exception as exc:
            print(f"[WARN] Hugging Face {kind}s: {exc}")
    return results
