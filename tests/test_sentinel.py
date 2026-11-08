#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel import (
    parse_transcript_tokens,
    get_status_info,
    render_meter,
    get_metrics_payload,
    DEFAULT_WARN_THRESHOLD,
    DEFAULT_DANGER_THRESHOLD
)

class TestClaudeTokenSentinel(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_parse_transcript_jsonl(self):
        log_file = self.tmppath / "session.jsonl"
        lines = [
            json.dumps({"type": "turn", "usage": {"input_tokens": 1200, "output_tokens": 300}}),
            json.dumps({"type": "turn", "message": {"usage": {"input_tokens": 800, "output_tokens": 150}}}),
            "corrupted line",
            ""
        ]
        log_file.write_text("\n".join(lines), encoding="utf-8")

        inp, out, turns = parse_transcript_tokens(str(log_file))
        self.assertEqual(inp, 2000)
        self.assertEqual(out, 450)
        self.assertEqual(turns, 2)

    def test_parse_transcript_formatted_json(self):
        json_file = self.tmppath / "history.json"
        data = [
            {"usage": {"input_tokens": 5000, "output_tokens": 500}},
            {"usage": {"input_tokens": 2500, "output_tokens": 250}}
        ]
        json_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        inp, out, turns = parse_transcript_tokens(str(json_file))
        self.assertEqual(inp, 7500)
        self.assertEqual(out, 750)
        self.assertEqual(turns, 2)

    def test_parse_transcript_nonexistent(self):
        inp, out, turns = parse_transcript_tokens("/non/existent/path.jsonl")
        self.assertEqual((inp, out, turns), (0, 0, 0))

    def test_get_status_info(self):
        status, _, _ = get_status_info(50000, DEFAULT_WARN_THRESHOLD, DEFAULT_DANGER_THRESHOLD)
        self.assertEqual(status, "optimal")

        status, _, _ = get_status_info(90000, DEFAULT_WARN_THRESHOLD, DEFAULT_DANGER_THRESHOLD)
        self.assertEqual(status, "warning")

        status, _, _ = get_status_info(150000, DEFAULT_WARN_THRESHOLD, DEFAULT_DANGER_THRESHOLD)
        self.assertEqual(status, "critical")

    def test_render_meter(self):
        meter = render_meter(100000, max_tokens=200000, bar_length=20)
        self.assertIn("50.0%", meter)
        self.assertIn("█", meter)

    def test_get_metrics_payload(self):
        payload = get_metrics_payload(
            input_tokens=100000,
            output_tokens=10000,
            turns=12,
            source_label="unit-test"
        )
        self.assertEqual(payload["prompt_tokens"], 100000)
        self.assertEqual(payload["completion_tokens"], 10000)
        self.assertEqual(payload["total_tokens"], 110000)
        self.assertEqual(payload["turns"], 12)
        self.assertEqual(payload["status"], "warning")
        self.assertGreater(payload["estimated_cost_usd"], 0)

if __name__ == "__main__":
    unittest.main()
