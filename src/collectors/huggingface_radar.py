from huggingface_hub import HfApi

from src.profile import (
    load_profile,
)


def datetime_value(value):

    if value is None:
        return None

    if hasattr(
        value,
        "isoformat",
    ):
        return value.isoformat()

    return str(value)


def collect_huggingface() -> list[dict]:

    profile = load_profile()

    limits = profile.get(
        "limits",
        {},
    )

    model_limit = int(
        limits.get(
            "hf_models",
            15,
        )
    )

    space_limit = int(
        limits.get(
            "hf_spaces",
            10,
        )
    )

    api = HfApi()

    results = []

    # ========================================================
    # MODELS
    # ========================================================

    try:
        try:
            models = list(
                api.list_models(
                    sort="trending_score",
                    limit=model_limit,
                )
            )

        except Exception:
            # Nếu API/library version không hỗ trợ
            # trending_score thì fallback.

            models = list(
                api.list_models(
                    sort="downloads",
                    limit=model_limit,
                )
            )

        for model in models:
            model_id = model.id

            results.append(
                {
                    "source_platform": "huggingface",
                    "external_id": f"model:{model_id}",
                    "item_type_hint": "AI_MODEL",
                    "name": model_id,
                    "title": model_id,
                    "description": ("Hugging Face model đang có tín hiệu đáng chú ý."),
                    "url": (f"https://huggingface.co/{model_id}"),
                    "published_at": datetime_value(
                        getattr(
                            model,
                            "created_at",
                            None,
                        )
                    ),
                    "metadata": {
                        "downloads": (
                            getattr(
                                model,
                                "downloads",
                                0,
                            )
                            or 0
                        ),
                        "likes": (
                            getattr(
                                model,
                                "likes",
                                0,
                            )
                            or 0
                        ),
                        "pipeline_tag": getattr(
                            model,
                            "pipeline_tag",
                            None,
                        ),
                        "trending_score": (
                            getattr(
                                model,
                                "trending_score",
                                0,
                            )
                            or 0
                        ),
                        "tags": list(
                            getattr(
                                model,
                                "tags",
                                [],
                            )
                            or []
                        )[:30],
                    },
                }
            )

    except Exception as exc:
        print(f"[WARN] Hugging Face models: {exc}")

    # ========================================================
    # SPACES = TOOL / DEMO
    # ========================================================

    try:
        try:
            spaces = list(
                api.list_spaces(
                    sort="trending_score",
                    limit=space_limit,
                )
            )

        except Exception:
            spaces = list(
                api.list_spaces(
                    sort="likes",
                    limit=space_limit,
                )
            )

        for space in spaces:
            space_id = space.id

            results.append(
                {
                    "source_platform": "huggingface",
                    "external_id": f"space:{space_id}",
                    "item_type_hint": "DEV_TOOL",
                    "name": space_id,
                    "title": space_id,
                    "description": ("Hugging Face Space / AI tool đang được chú ý."),
                    "url": (f"https://huggingface.co/spaces/{space_id}"),
                    "published_at": datetime_value(
                        getattr(
                            space,
                            "created_at",
                            None,
                        )
                    ),
                    "metadata": {
                        "likes": (
                            getattr(
                                space,
                                "likes",
                                0,
                            )
                            or 0
                        ),
                        "trending_score": (
                            getattr(
                                space,
                                "trending_score",
                                0,
                            )
                            or 0
                        ),
                        "tags": list(
                            getattr(
                                space,
                                "tags",
                                [],
                            )
                            or []
                        )[:30],
                    },
                }
            )

    except Exception as exc:
        print(f"[WARN] Hugging Face spaces: {exc}")

    return results
