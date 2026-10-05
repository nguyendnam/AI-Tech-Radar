import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from src.collectors.huggingface import collect_huggingface


class HuggingFaceTests(unittest.TestCase):
    @patch("src.collectors.huggingface.HfApi")
    def test_models_and_spaces_keep_their_types_and_metadata(self, api):
        created = datetime(2026, 10, 6, tzinfo=timezone.utc)
        api.return_value.list_models.return_value = [
            SimpleNamespace(
                id="org/model",
                created_at=created,
                likes=10,
                downloads=100,
                pipeline_tag="text-generation",
                tags=["llm"],
                trending_score=2,
            )
        ]
        api.return_value.list_spaces.return_value = [SimpleNamespace(id="org/tool")]
        model, space = collect_huggingface()
        self.assertEqual(model["item_type_hint"], "AI_MODEL")
        self.assertEqual(model["metadata"]["downloads"], 100)
        self.assertEqual(model["published_at"], created.isoformat())
        self.assertEqual(space["item_type_hint"], "DEV_TOOL")
        self.assertEqual(space["url"], "https://huggingface.co/spaces/org/tool")
        self.assertEqual(space["external_id"], "space:org/tool")
        self.assertIsNone(space["published_at"])
        self.assertNotIn("downloads", space["metadata"])

    @patch("src.collectors.huggingface.HfApi")
    def test_fallback_sort_keeps_both_sources(self, api):
        api.return_value.list_models.side_effect = [
            ValueError("unsupported sort"),
            [SimpleNamespace(id="org/model")],
        ]
        api.return_value.list_spaces.return_value = [SimpleNamespace(id="org/tool")]
        self.assertEqual(len(collect_huggingface()), 2)
        self.assertEqual(
            api.return_value.list_models.call_args.kwargs["sort"], "downloads"
        )


if __name__ == "__main__":
    unittest.main()
