import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from pglast import parse_sql

from src import ai, database, pipeline
from src.digest import select_balanced
from src.scoring import keyword_match
from src.telegram_sender import _send_with_retry, _split_message


def candidate(kind="NEWS", number=1):
    return {
        "source_platform": "rss",
        "external_id": str(number),
        "url": f"https://example.com/{number}",
        "title": "AI agent update",
        "description": "new coding agent",
        "item_type_hint": kind,
        "metadata": {},
    }


class PipelineTests(unittest.TestCase):
    def test_emoji_message_splits_within_telegram_limit(self):
        text = "🧠" * 3000
        chunks = _split_message(text)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(
            all(len(chunk.encode("utf-16-le")) // 2 <= 3500 for chunk in chunks)
        )

    @patch("src.telegram_sender.time.sleep")
    @patch("src.telegram_sender.requests.post")
    def test_telegram_rate_limit_retries(self, post, sleep):
        post.side_effect = [
            SimpleNamespace(
                status_code=429, json=lambda: {"parameters": {"retry_after": 2}}
            ),
            SimpleNamespace(status_code=200, json=lambda: {"ok": True}),
        ]
        _send_with_retry("https://example.com", {})
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_rss_hn_deduplicates_tracking_urls(self):
        rss = {
            "url": "https://example.com/story?utm_source=rss",
            "title": "AI",
            "source": "OpenAI",
        }
        hn = {**rss, "url": "https://example.com/story#hn", "source": "Hacker News"}
        rows = list(pipeline.rank_candidates([rss, hn]))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["item_type_hint"], "NEWS")

    def test_arxiv_is_paper(self):
        row = pipeline.normalize_candidate(
            {
                "url": "https://arxiv.org/abs/1",
                "title": "Research",
                "source": "arXiv cs.AI",
            }
        )
        self.assertEqual(row["item_type_hint"], "PAPER")

    def test_source_types_share_analysis_budget_fairly(self):
        rows = [candidate("AI_MODEL", n) for n in range(10)] + [candidate("NEWS", 20)]
        ranked = list(pipeline.rank_candidates(rows))
        self.assertIn("NEWS", [row["item_type_hint"] for row in ranked[:2]])

    def test_keyword_boundaries(self):
        self.assertFalse(keyword_match("go", "google"))
        self.assertFalse(keyword_match("ai", "chair"))
        self.assertTrue(keyword_match("go", "Go compiler"))

    def test_ai_normalizes_false_nonfinite_and_source_type(self):
        row = ai.normalize_analysis(
            {
                "relevant": "false",
                "item_type": "GITHUB_REPO",
                "radar_status": "ADOPT",
                "relevance_score": float("nan"),
                "importance_score": 50,
            },
            candidate(),
        )
        self.assertFalse(row["relevant"])
        self.assertEqual(row["item_type"], "NEWS")
        self.assertEqual(row["radar_status"], "WATCH")
        self.assertEqual(row["relevance_score"], 0)
        self.assertEqual(row["importance_score"], 10)

    def test_language_search_does_not_force_language(self):
        row = ai.normalize_analysis(
            {"item_type": "DEV_TOOL"}, candidate("LANGUAGE_CANDIDATE")
        )
        self.assertEqual(row["item_type"], "DEV_TOOL")

    def test_small_legitimate_scores_are_not_multiplied(self):
        row = ai.normalize_analysis({key: 0.5 for key in ai.WEIGHTS}, candidate())
        self.assertEqual(row["final_score"], 0.5)

    def test_zero_digest_limit(self):
        self.assertEqual(select_balanced([candidate()], 0), [])

    @patch("src.pipeline.database")
    @patch("src.pipeline.collect_all")
    @patch("src.pipeline.analyze_item", side_effect=RuntimeError("AI unavailable"))
    def test_failed_ai_calls_consume_budget_and_fail_job(self, analyze, collect, db):
        limits = {
            "limits": {
                "min_prefilter_score": 0,
                "ai_analyses_per_run": 2,
                "min_store_score": 0,
            }
        }
        collect.return_value = [candidate(number=n) for n in range(5)]
        db.find_item.return_value = None
        with (
            patch("src.pipeline.load_profile", return_value=limits),
            self.assertRaises(RuntimeError),
        ):
            pipeline.collect()
        self.assertEqual(analyze.call_count, 2)

    @patch("src.pipeline.database")
    @patch("src.pipeline.collect_all")
    @patch("src.pipeline.analyze_item")
    def test_existing_items_refresh_without_ai(self, analyze, collect, db):
        collect.return_value = [candidate()]
        db.find_item.return_value = {"id": "known"}
        pipeline.collect()
        db.observe_item.assert_called_once()
        analyze.assert_not_called()

    @patch("src.pipeline.database")
    @patch("src.pipeline.send_telegram", side_effect=RuntimeError("failed"))
    def test_failed_send_is_not_marked(self, send, db):
        db.get_unsent_items.return_value = [
            {**candidate(), "id": "id", "item_type": "NEWS", "final_score": 8}
        ]
        with self.assertRaises(RuntimeError):
            pipeline.digest()
        db.mark_sent.assert_not_called()

    @patch("src.pipeline.database")
    @patch("src.pipeline.send_telegram")
    def test_success_marks_sent_after_delivery(self, send, db):
        db.get_unsent_items.return_value = [
            {**candidate(), "id": "id", "item_type": "NEWS", "final_score": 8}
        ]
        order = []
        send.side_effect = lambda _: order.append("send")
        db.mark_sent.side_effect = lambda _: order.append("mark")
        pipeline.digest()
        self.assertEqual(order, ["send", "mark"])

    @patch("src.telegram_sender.requests.post")
    def test_telegram_api_failure_is_not_success(self, post):
        post.return_value = SimpleNamespace(status_code=200, json=lambda: {"ok": False})
        with self.assertRaises(RuntimeError):
            _send_with_retry("https://example.com", {}, retries=1)

    def test_single_sql_and_workflow_entrypoints(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(len(list((root / "sql").glob("*.sql"))), 1)
        statements = parse_sql((root / "sql/schema.sql").read_text(encoding="utf-8"))
        self.assertEqual(
            sum(type(s.stmt).__name__ == "CreateStmt" for s in statements), 1
        )
        for name, command in [
            ("collect-news", "collect"),
            ("daily-digest", "digest"),
            ("cleanup", "cleanup"),
        ]:
            workflow = yaml.safe_load(
                (root / f".github/workflows/{name}.yml").read_text(encoding="utf-8")
            )
            self.assertEqual(
                workflow["jobs"][command]["steps"][-1]["run"], f"python {command}.py"
            )

    @patch("src.database.get_client")
    def test_cleanup_protects_saved_and_adopt(self, client):
        query = client.return_value.table.return_value
        query.delete.return_value = query
        query.eq.return_value = query
        query.neq.return_value = query
        query.lt.return_value = query
        query.gte.return_value = query
        query.execute.return_value.data = []
        database.cleanup_items(7, 9, 90)
        query.eq.assert_called_with("saved", False)
        query.neq.assert_called_with("radar_status", "ADOPT")


if __name__ == "__main__":
    unittest.main()
