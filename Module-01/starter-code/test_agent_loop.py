import io
import os
import ssl
import unittest
import urllib
from contextlib import redirect_stdout
from unittest import mock

import agent_loop_starter as agent


class AgentLoopTests(unittest.TestCase):
    def test_calculator_evaluates_safe_expression(self):
        self.assertEqual(agent.calculator("23*19"), "437")
        self.assertEqual(agent.calculator("(23*19)+100"), "537")

    def test_run_agent_uses_multi_step_fallback_for_lab_question(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENROUTER_API_KEY", None)
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = agent.run_agent("What is (23 * 19) + 100, and is that more than 500?")
            self.assertEqual(result, "537, yes, more than 500.")
            self.assertIn("llm_calls=", buf.getvalue())

    def test_call_model_retries_with_unverified_ssl_on_cert_error(self):
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"choices": [{"message": {"content": "ok"}}]}'

        def fake_urlopen(request, context=None, timeout=None):
            if context is None:
                raise urllib.error.URLError(ssl.SSLError("cert issue"))
            return DummyResponse()

        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy"}, clear=True):
            with mock.patch("agent_loop_starter.urllib.request.urlopen", side_effect=fake_urlopen):
                self.assertEqual(agent.call_model([{"role": "user", "content": "hi"}]), "ok")


if __name__ == "__main__":
    unittest.main()
