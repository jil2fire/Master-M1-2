import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class ChatRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_empty_data_does_not_call_model_or_use_quota(self):
        with patch("routers.chat.current_summary", return_value={"count": 0, "trend_message": "기록 없음"}), \
             patch("routers.chat.answer") as answer, \
             patch("routers.chat.store.claim_chat_quota") as quota:
            response = self.client.post("/api/chat", json={"message": "최근 추세는?"})
            self.assertEqual(response.status_code, 409)
            answer.assert_not_called()
            quota.assert_not_called()

    def test_answer_and_saved_summary_share_request_snapshot(self):
        summary = {"count": 1, "as_of_date": "2025-04-30", "trend": None}
        saved = {"conversation_id": "c1", "answer": "답변", "saved_at": "2025-04-30T00:00:00+00:00"}
        with patch("routers.chat.current_summary", return_value=summary), \
             patch("routers.chat.answer", return_value="답변") as answer, \
             patch("routers.chat.store.claim_chat_quota"), \
             patch("routers.chat.store.append_chat", return_value=saved) as append:
            response = self.client.post("/api/chat", json={"message": "최근 추세는?"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), saved)
            self.assertEqual(answer.call_args.args[2], summary)
            self.assertEqual(append.call_args.args[4]["as_of_date"], summary["as_of_date"])
            self.assertIn("calculated_at", append.call_args.args[4])


if __name__ == "__main__":
    unittest.main()
