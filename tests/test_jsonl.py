import json
import shutil
import tempfile
import unittest
from pathlib import Path

from assaystone.audit import load_audit_traces
from assaystone.jsonl import read_jsonl

REPO = Path(__file__).resolve().parent.parent
CODE_BASELINE = REPO / "examples" / "code_agent" / "baseline"
AUDIT_BASELINE = REPO / "examples" / "audit" / "baseline"


def assistant_entry(text: str, session: str = "s1") -> dict:
    return {
        "type": "assistant",
        "sessionId": session,
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
        },
    }


class JsonlTest(unittest.TestCase):
    def test_unicode_line_boundary_inside_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                json.dumps(assistant_entry("a\u0085b"), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            entries, errors = read_jsonl(path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(errors, [])
            self.assertIn("\u0085", entries[0]["message"]["content"][0]["text"])

    def test_bad_line_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                "{not json}\n" + json.dumps(assistant_entry("ok")) + "\n",
                encoding="utf-8",
            )
            entries, errors = read_jsonl(path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(len(errors), 1)

    def test_audit_skips_bad_jsonl_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                "{not json}\n" + json.dumps(assistant_entry("Done.")) + "\n",
                encoding="utf-8",
            )
            traces = load_audit_traces(path, baseline=AUDIT_BASELINE)
            self.assertEqual(len(traces), 1)
            self.assertTrue(traces[0].evidence.get("parse_warnings"))

    def test_directory_skips_unreadable_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "traces"
            directory.mkdir()
            shutil.copy(
                REPO / "examples" / "code_agent" / "traces" / "t01-correct.json",
                directory / "trace.json",
            )
            (directory / "package.json").write_text("{}\n", encoding="utf-8")
            traces = load_audit_traces(
                directory, format="trace", baseline=CODE_BASELINE
            )
            self.assertEqual(len(traces), 1)
            self.assertEqual(traces[0].id, "t01-correct")


if __name__ == "__main__":
    unittest.main()
