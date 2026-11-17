import contextlib
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import usage_report  # noqa: E402


def assistant(message_id, request_id, model="claude-sonnet-4", content=None, **usage):
    usage.setdefault("input_tokens", 10)
    usage.setdefault("output_tokens", 5)
    message = {"id": message_id, "model": model, "usage": usage, "content": content or [{"type": "text", "text": "ok"}]}
    return {"type": "assistant", "requestId": request_id, "message": message}


def skill_call(name):
    return [{"type": "tool_use", "name": "Skill", "input": {"skill": name}}]


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


class UsageReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.claude = Path(self.tmp.name, "projects")
        self.codex = Path(self.tmp.name, "sessions")
        self.project = self.claude / "proj"
        self.project.mkdir(parents=True)

    def write(self, path, entries, raw=()):
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(entry) for entry in entries] + list(raw)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def rows(self, days=7):
        report = usage_report.build_report(days, self.claude, self.codex)
        return {row["workflow"]: row for row in report["hosts"][0]["workflows"]}

    def test_a_response_repeated_on_every_content_block_counts_once(self):
        self.write(self.project / "s1.jsonl", [assistant("m1", "r1"), assistant("m1", "r1"), assistant("m2", "r2")],
                   raw=["not json", "{broken"])
        row = self.rows()["other"]
        self.assertEqual((row["sessions"], row["requests"], row["input"], row["output"]), (1, 2, 20, 10))

    def test_subagent_transcripts_roll_into_their_parent_session(self):
        self.write(self.project / "s1.jsonl", [assistant("m1", "r1")])
        self.write(self.project / "s1" / "subagents" / "agent-a.jsonl", [assistant("m2", "r2"), assistant("m3", "r3")])
        row = self.rows()["other"]
        self.assertEqual((row["sessions"], row["requests"]), (1, 3))

    def test_sessions_are_attributed_to_the_first_tinker_workflow(self):
        self.write(self.project / "a.jsonl", [assistant("m1", "r1", content=skill_call("tinker:tinker-implement")),
                                              assistant("m2", "r2", content=skill_call("tinker:review"))])
        self.write(self.project / "b.jsonl", [user("<command-name>/tinker:investigate</command-name>"), assistant("m3", "r3")])
        self.write(self.project / "c.jsonl", [assistant("m4", "r4", content=skill_call("tinker"))])
        self.write(self.project / "d.jsonl", [assistant("m5", "r5", content=skill_call("other:thing"))])
        self.write(self.project / "e.jsonl", [assistant("m6", "r6")])
        self.write(self.project / "f.jsonl", [assistant("m7", "r7")])
        self.write(self.project / "f" / "subagents" / "agent-x.jsonl", [user("<command-name>/tinker-shape</command-name>")])
        rows = self.rows()
        self.assertEqual(rows["implement"]["sessions"], 1)
        self.assertEqual(rows["investigate"]["sessions"], 1)
        self.assertEqual(rows["front-door"]["sessions"], 1)
        self.assertEqual(rows["shape"]["sessions"], 1)
        self.assertEqual(rows["other"]["sessions"], 2)
        self.assertNotIn("review", rows)

    def test_workflow_names(self):
        for name, expected in [("tinker", "front-door"), ("tinker:tinker", "front-door"), ("tinker-implement", "implement"),
                               ("tinker:tinker-bug-fix", "bug-fix"), ("other", None), ("tinkerbell", None)]:
            self.assertEqual(usage_report.workflow_from_name(name), expected, name)

    def test_cost_arithmetic_with_five_minute_and_one_hour_cache_writes(self):
        usage = {"input": 1_000_000, "output": 1_000_000, "cache_read": 1_000_000, "cache_write": 1_000_000,
                 "cache_write_1h": 400_000}
        # sonnet: 2 in + 10 out + 0.10 read + 600k 5m writes at 2.5 + 400k 1h writes at 4
        self.assertAlmostEqual(usage_report.request_cost("claude-sonnet-4", usage), 2 + 10 + 0.10 + 1.5 + 1.6)
        unsplit = dict(usage, cache_write_1h=0)
        self.assertAlmostEqual(usage_report.request_cost("claude-opus-4", unsplit), 4 + 20 + 0.20 + 5.0)
        self.assertIsNone(usage_report.request_cost("gpt-9", usage))

    def test_cost_flows_through_the_report_with_the_cache_split(self):
        self.write(self.project / "s1.jsonl", [assistant(
            "m1", "r1", model="claude-haiku-4", input_tokens=1_000_000, output_tokens=0,
            cache_creation_input_tokens=1_000_000, cache_creation={"ephemeral_1h_input_tokens": 1_000_000,
                                                                   "ephemeral_5m_input_tokens": 0})])
        row = self.rows()["other"]
        self.assertAlmostEqual(row["est_usd"], 0.10 + 0.20)
        self.assertEqual(row["avg_context"], 2_000_000)

    def test_unknown_model_counts_tokens_but_no_cost_and_is_listed(self):
        self.write(self.project / "s1.jsonl", [assistant("m1", "r1", model="mystery-1")])
        report = usage_report.build_report(7, self.claude, self.codex)
        row = report["hosts"][0]["workflows"][0]
        self.assertEqual((row["input"], row["est_usd"]), (10, 0.0))
        self.assertEqual(report["hosts"][0]["unpriced_models"], ["mystery-1"])

    def test_days_window_uses_file_modification_time(self):
        old = self.write(self.project / "old.jsonl", [assistant("m1", "r1")])
        self.write(self.project / "new.jsonl", [assistant("m2", "r2")])
        past = time.time() - 10 * 86400
        os.utime(old, (past, past))
        self.assertEqual(self.rows(days=7)["other"]["sessions"], 1)
        self.assertEqual(self.rows(days=30)["other"]["sessions"], 2)

    def codex_file(self, name, totals, user_text=None, session_id="s-1"):
        entries = [{"type": "session_meta", "payload": {"session_id": session_id, "id": name}},
                   {"type": "turn_context", "payload": {"model": "gpt-6"}}]
        if user_text:
            entries.append({"type": "response_item", "payload": {"type": "message", "role": "user",
                                                                 "content": [{"type": "input_text", "text": user_text}]}})
        for index, (input_tokens, cached, output) in enumerate(totals):
            total = {"input_tokens": input_tokens, "cached_input_tokens": cached, "cache_write_input_tokens": 0,
                     "output_tokens": output, "total_tokens": input_tokens + output}
            entries.append({"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": total}}})
        return self.write(self.codex / "2026" / "11" / "12" / f"rollout-{name}.jsonl", entries)

    def test_codex_uses_the_last_cumulative_total_and_attributes_the_skill(self):
        self.codex_file("a", [(100, 50, 10), (300, 200, 40), (700, 600, 90)],
                        user_text="<skill>\n<name>tinker:tinker-investigate</name>\n</skill>")
        report = usage_report.build_report(7, self.claude, self.codex)
        row = report["hosts"][1]["workflows"][0]
        self.assertEqual(row["workflow"], "investigate")
        self.assertEqual((row["requests"], row["input"], row["cache_read"], row["output"]), (3, 100, 600, 90))
        self.assertEqual(row["avg_context"], round(700 / 3))
        self.assertIsNone(row["est_usd"])

    def test_codex_subagent_files_join_their_session(self):
        self.codex_file("a", [(100, 0, 10)], user_text="[$tinker:tinker](skills/tinker/SKILL.md)")
        self.codex_file("b", [(50, 0, 5)], session_id="s-1")
        row = usage_report.build_report(7, self.claude, self.codex)["hosts"][1]["workflows"][0]
        self.assertEqual((row["workflow"], row["sessions"], row["input"]), ("front-door", 1, 150))

    def test_json_output_shape(self):
        self.write(self.project / "s1.jsonl", [assistant("m1", "r1")])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = usage_report.main(["--json", "--claude-dir", str(self.claude), "--codex-dir", str(self.codex), "--days", "3"])
        data = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual((data["days"], data["prices_as_of"]), (3, usage_report.PRICES_AS_OF))
        self.assertEqual([host["host"] for host in data["hosts"]], ["claude", "codex", "antigravity"])
        self.assertFalse(data["hosts"][2]["supported"])
        row = data["hosts"][0]["workflows"][0]
        for key in ("workflow", "sessions", "requests", "avg_context", "output", "est_usd", "usd_per_session"):
            self.assertIn(key, row)

    def test_table_output_never_prints_message_content_and_notes_antigravity(self):
        self.write(self.project / "s1.jsonl", [assistant("m1", "r1", content=[{"type": "text", "text": "SECRET-TEXT"}])])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            usage_report.main(["--claude-dir", str(self.claude), "--codex-dir", str(self.codex)])
        self.assertNotIn("SECRET-TEXT", out.getvalue())
        self.assertIn("antigravity: not supported", out.getvalue())
        self.assertIn("| other | 1 | 1 |", out.getvalue())


if __name__ == "__main__":
    unittest.main()
