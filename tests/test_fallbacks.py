"""Fallback-chain tests (no network): `python3 -m unittest tests.test_fallbacks`."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import common
from pipeline.common import AllModelsFailed, RetryableError, model_chain, with_fallbacks


class FallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runs = Path(self.tmp.name) / "runs.jsonl"
        self.p1 = mock.patch.object(common, "RUNS", self.runs)
        self.p2 = mock.patch.object(common.time, "sleep", lambda s: None)  # no real waiting
        self.p1.start(); self.p2.start()

    def tearDown(self):
        self.p1.stop(); self.p2.stop(); self.tmp.cleanup()

    def log(self):
        return [json.loads(l) for l in self.runs.read_text().splitlines()]

    def test_overloaded_primary_falls_back(self):
        calls = []

        def fn(model):
            calls.append(model)
            if model == "primary":
                raise RetryableError("HTTP 503 high demand")
            return "audio"

        result, used = with_fallbacks("narration", "s01", "gemini", ["primary", "backup"], {}, fn,
                                      attempts_per_model=2)
        self.assertEqual((result, used), ("audio", "backup"))
        self.assertEqual(calls, ["primary", "primary", "backup"])  # retried primary once, then switched
        log = self.log()
        self.assertEqual([r["status"] for r in log], ["error", "ok"])
        self.assertEqual(log[1]["params"]["fallback_from"], "primary")

    def test_fatal_error_skips_retries(self):
        calls = []

        def fn(model):
            calls.append(model)
            if model == "bad-id":
                raise RuntimeError("HTTP 404 model not found")
            return "ok"

        _, used = with_fallbacks("smoke", "t", "gemini", ["bad-id", "good"], {}, fn)
        self.assertEqual(used, "good")
        self.assertEqual(calls, ["bad-id", "good"])  # 404 is not retried

    def test_all_fail_raises(self):
        def fn(model):
            raise RetryableError("503")
        with self.assertRaises(AllModelsFailed):
            with_fallbacks("x", "y", "gemini", ["a", "b"], {}, fn, attempts_per_model=1)
        self.assertEqual(len(self.log()), 2)

    def test_chain_from_storyboard(self):
        self.assertEqual(model_chain({"tts": "a", "tts_fallbacks": ["b", "a", "c"]}, "tts"), ["a", "b", "c"])
        self.assertEqual(model_chain({"tts": "a"}, "tts"), ["a"])


if __name__ == "__main__":
    unittest.main()
