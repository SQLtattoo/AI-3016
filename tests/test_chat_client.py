import importlib
import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import Mock, patch

from openai.types import CompletionUsage


class ChatClientTokenTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module("3b_chat_client")

    def response(self, input_tokens=0, output_tokens=0, reply="Reply", usage_available=True):
        usage = (
            CompletionUsage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            )
            if usage_available
            else None
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
            usage=usage,
        )

    def run_chat(self, responses, inputs):
        client = Mock()
        responses = iter(responses)
        requests = []

        def create(*, model, messages):
            requests.append({
                "model": model,
                "messages": [message.copy() for message in messages],
            })
            return next(responses)

        client.chat.completions.create.side_effect = create
        output = io.StringIO()
        with (
            patch.object(self.module, "get_client", return_value=client),
            patch("builtins.input", side_effect=inputs),
            redirect_stdout(output),
        ):
            self.module.main()
        return output.getvalue(), requests

    def test_per_call_arithmetic_input_growth_and_cumulative_usage(self):
        output, requests = self.run_chat(
            [self.response(100, 20, "First reply"), self.response(145, 15, "Second reply")],
            ["First question", "Follow-up", "exit"],
        )

        self.assertIn("Call 1 tokens: input 100 + output 20 = 120", output)
        self.assertIn("Cumulative tokens: input 100 + output 20 = 120", output)
        self.assertIn("Call 2 tokens: input 145 + output 15 = 160", output)
        self.assertIn("Input change since previous call: +45 tokens", output)
        self.assertIn("Cumulative tokens: input 245 + output 35 = 280", output)
        self.assertIn("cumulative usage counts it again", output)
        self.assertIn("aria > First reply", output)
        self.assertIn("aria > Second reply", output)
        self.assertEqual(requests[0]["model"], self.module.CHAT_DEPLOYMENT)
        self.assertEqual(requests[0]["messages"], [
            {"role": "system", "content": self.module.SYSTEM_PROMPT},
            {"role": "user", "content": "First question"},
        ])
        self.assertEqual(requests[1]["messages"], [
            *requests[0]["messages"],
            {"role": "assistant", "content": "First reply"},
            {"role": "user", "content": "Follow-up"},
        ])

    def test_missing_usage_is_explicit_and_later_totals_remain_partial(self):
        output, requests = self.run_chat(
            [
                self.response(100, 20),
                self.response(reply="Unmetered reply", usage_available=False),
                self.response(200, 30),
            ],
            ["First", "Second", "Third", "exit"],
        )

        self.assertIn("Call 2 tokens: unavailable (API did not return usage)", output)
        self.assertIn("Cumulative usage is incomplete", output)
        self.assertIn(
            "Cumulative tokens (reported calls only): input 300 + output 50 = 350",
            output,
        )
        self.assertNotIn("Input change since previous call", output)
        self.assertIn(
            {"role": "assistant", "content": "Unmetered reply"},
            requests[2]["messages"],
        )

    def test_zero_usage_is_not_treated_as_missing(self):
        output, _ = self.run_chat([self.response()], ["Question", "exit"])
        self.assertIn("Call 1 tokens: input 0 + output 0 = 0", output)
        self.assertIn("Cumulative tokens: input 0 + output 0 = 0", output)
        self.assertNotIn("unavailable", output)

    def test_blank_input_and_exit_do_not_make_calls(self):
        output, requests = self.run_chat([], [" ", " QUIT "])
        self.assertEqual(requests, [])
        self.assertNotIn("Call 1 tokens", output)

    def test_terminal_interrupts_do_not_make_calls(self):
        for error in (EOFError(), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                _, requests = self.run_chat([], [error])
                self.assertEqual(requests, [])

    def test_counters_reset_for_each_session(self):
        for _ in range(2):
            output, _ = self.run_chat([self.response(10, 5)], ["Question", "exit"])
            self.assertIn("Call 1 tokens: input 10 + output 5 = 15", output)
            self.assertIn("Cumulative tokens: input 10 + output 5 = 15", output)


if __name__ == "__main__":
    unittest.main()
