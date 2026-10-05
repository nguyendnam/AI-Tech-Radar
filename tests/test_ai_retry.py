import unittest
from types import SimpleNamespace
from unittest.mock import patch

from google.genai import errors

from src import ai, pipeline


def api_error(code, message="test API error", retry_delay=None):
    details = [{"retryDelay": retry_delay}] if retry_delay else []
    error_type = errors.ClientError if code < 500 else errors.ServerError
    return error_type(
        code, {"error": {"message": message, "status": "TEST", "details": details}}
    )


class AIRetryTests(unittest.TestCase):
    @patch("src.ai.time.sleep")
    @patch("src.ai.get_client")
    def test_rate_limit_retries_and_disables_afc(self, client, sleep):
        generate = client.return_value.models.generate_content
        generate.side_effect = [
            api_error(429, retry_delay="12s"),
            SimpleNamespace(text="{}"),
        ]
        session = ai.AnalysisSession(interval=0)
        session.generate("test")
        self.assertEqual(session.requests, 2)
        self.assertIn(unittest.mock.call(12), sleep.call_args_list)
        self.assertTrue(
            generate.call_args.kwargs["config"].automatic_function_calling.disable
        )

    @patch("src.ai.time.sleep")
    @patch("src.ai.get_client")
    def test_retries_share_budget(self, client, sleep):
        client.return_value.models.generate_content.side_effect = api_error(503)
        session = ai.AnalysisSession(limit=2, interval=0)
        with self.assertRaises(ai.AIBudgetExhausted):
            session.generate("test")
        self.assertEqual(session.requests, 2)
        self.assertEqual(client.return_value.models.generate_content.call_count, 2)

    @patch("src.ai.time.sleep")
    @patch("src.ai.get_client")
    def test_persistent_quota_pauses_later_requests(self, client, sleep):
        client.return_value.models.generate_content.side_effect = api_error(429)
        session = ai.AnalysisSession(interval=0)
        with self.assertRaises(ai.TemporaryAIError):
            session.generate("test")
        self.assertTrue(session.paused)
        with self.assertRaises(ai.AIBudgetExhausted):
            session.generate("another item")
        self.assertEqual(session.requests, 3)

    @patch("src.ai.time.sleep")
    @patch("src.ai.get_client")
    def test_invalid_key_fails_without_retry(self, client, sleep):
        client.return_value.models.generate_content.side_effect = api_error(403)
        with self.assertRaisesRegex(ai.AIConfigurationError, "HTTP 403"):
            ai.AnalysisSession().generate("test")
        self.assertEqual(client.return_value.models.generate_content.call_count, 1)
        sleep.assert_not_called()

    def test_error_message_redacts_key(self):
        with patch("src.ai.GEMINI_API_KEY", "private-key"):
            message = ai.api_error_message(
                api_error(400, "Rejected private-key key=other-secret")
            )
        self.assertNotIn("private-key", message)
        self.assertNotIn("other-secret", message)
        self.assertIn("HTTP 400", message)

    @patch("src.ai.time.sleep")
    @patch("src.ai.get_client")
    def test_long_retry_delay_defers_without_waiting(self, client, sleep):
        client.return_value.models.generate_content.side_effect = api_error(
            429, retry_delay="120s"
        )
        session = ai.AnalysisSession()
        with self.assertRaises(ai.TemporaryAIError):
            session.generate("test")
        sleep.assert_not_called()
        self.assertTrue(session.paused)

    @patch("src.pipeline.database")
    @patch("src.pipeline.collect_all")
    @patch("src.pipeline.analyze_item")
    def test_partial_transient_failure_keeps_successful_collection(
        self, analyze, collect, db
    ):
        collect.return_value = [
            {
                "source_platform": "rss",
                "external_id": str(n),
                "url": f"https://example.com/{n}",
                "title": "AI agent update",
                "item_type_hint": "NEWS",
                "metadata": {},
            }
            for n in range(2)
        ]
        db.find_item.return_value = None
        analyze.side_effect = [
            ai.TemporaryAIError("Gemini HTTP 429"),
            {"relevant": True, "final_score": 8},
        ]
        pipeline.collect()
        db.save_item.assert_called_once()

    @patch("src.pipeline.database")
    @patch("src.pipeline.collect_all")
    @patch("src.pipeline.analyze_item", side_effect=ai.TemporaryAIError("HTTP 503"))
    def test_total_transient_outage_still_fails(self, analyze, collect, db):
        collect.return_value = [
            {
                "source_platform": "rss",
                "external_id": "1",
                "url": "https://example.com/1",
                "title": "AI agent",
                "item_type_hint": "NEWS",
                "metadata": {},
            }
        ]
        db.find_item.return_value = None
        with self.assertRaises(RuntimeError):
            pipeline.collect()


if __name__ == "__main__":
    unittest.main()
