import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from openai import AuthenticationError

from errors import AppError
from services.ai_service import _create_response, answer


class AiServiceTests(unittest.TestCase):
    def test_authentication_failure_hides_provider_details(self):
        response = httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        provider_error = AuthenticationError("Incorrect API key sk-example", response=response, body={})
        client = Mock()
        client.responses.create.side_effect = provider_error
        with self.assertRaises(AppError) as captured:
            _create_response(client, input="test")
        self.assertEqual(captured.exception.status_code, 503)
        self.assertNotIn("sk-example", captured.exception.message)

    def test_summary_tool_reuses_frozen_snapshot(self):
        call = SimpleNamespace(type="function_call", name="get_reservation_summary", arguments="{}", call_id="call_1")
        first = SimpleNamespace(id="response_1", output=[call], output_text="")
        second = SimpleNamespace(id="response_2", output=[], output_text="데이터 최신일 2025-04-30 기준 감소했습니다.")
        options = {"ai_provider": "openai", "model": "test", "max_output_tokens": 300}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only"}), \
             patch("services.ai_service.settings", return_value=options), \
             patch("services.ai_service.OpenAI") as client:
            client.return_value.responses.create.side_effect = [first, second]
            snapshot = {"as_of_date": "2025-04-30", "count": 120}
            result = answer("최근 추세는?", [], snapshot, None)
            self.assertIn("감소", result)
            second_call = client.return_value.responses.create.call_args_list[1]
            self.assertEqual(second_call.kwargs["previous_response_id"], "response_1")
            self.assertEqual(json.loads(second_call.kwargs["input"][0]["output"]), snapshot)
            self.assertEqual(
                client.return_value.responses.create.call_args_list[0].kwargs["instructions"],
                second_call.kwargs["instructions"],
            )

    def test_codyssey_chat_completion_tool_cycle(self):
        tool = SimpleNamespace(id="call_1", function=SimpleNamespace(name="get_reservation_summary", arguments="{}"))
        first = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tool]))])
        second = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="데이터 최신일 2025-04-30 기준 감소", tool_calls=[]))])
        options = {
            "ai_provider": "codyssey", "openai_base_url": "https://copa.codyssey.kr/v1",
            "model": "gpt-5.4-mini", "max_output_tokens": 300,
        }
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only"}), \
             patch("services.ai_service.settings", return_value=options), \
             patch("services.ai_service.OpenAI") as client:
            client.return_value.chat.completions.create.side_effect = [first, second]
            snapshot = {"count": 120, "as_of_date": "2025-04-30"}
            result = answer("최근 추세는?", [], snapshot, None)
            self.assertIn("감소", result)
            self.assertEqual(client.call_args.kwargs["base_url"], options["openai_base_url"])
            calls = client.return_value.chat.completions.create.call_args_list
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0].kwargs["tools"][0]["function"]["strict"], True)
            self.assertEqual(json.loads(calls[1].kwargs["messages"][-1]["content"]), snapshot)
            self.assertEqual(calls[1].kwargs["messages"][-1]["tool_call_id"], "call_1")


if __name__ == "__main__":
    unittest.main()
