"""Codex and agy eval tests: recorded host output under tests/fixtures/eval_hosts stands in for the hosts and a fake
`claude` for the judge, so no test spends model usage.

These prove the parsing of each host's event stream, the local graders and their per-host mapping (a tool with no
observable event is n/a, never a pass), the judge's vote reading, and that the gate never compares or accepts across
hosts; they do not run a case against a model.
"""
import json
import os
from pathlib import Path
import re
import shutil
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import eval_hosts  # noqa: E402
import eval_live  # noqa: E402
from test_eval_live import PYTHON, TempCase, write_case  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "eval_hosts"
FAKE_JUDGE = r'''
import json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
replies = json.loads((here / "judge.json").read_text(encoding="utf-8"))
count = here / "count.txt"
n = int(count.read_text()) if count.exists() else 0
count.write_text(str(n + 1))
with open(here / "judge.log", "a", encoding="utf-8") as log:
    log.write(json.dumps({"args": sys.argv[1:], "stdin": sys.stdin.read()}) + "\n")
print(json.dumps({"type": "result", "result": replies[n % len(replies)], "total_cost_usd": 0.001}))
'''


def case_of(name):
    return eval_live.read_case(ROOT / "evals" / "live" / name / "case.yaml")


def copy_fixture(name, dest):
    shutil.copytree(FIXTURES / name, dest)
    (dest / "work").mkdir(exist_ok=True)
    return dest


class CaseFileTests(unittest.TestCase):
    def test_every_case_has_a_prompt_and_python_compiles_its_patterns(self):
        for folder in eval_live.case_dirs(ROOT):
            with self.subTest(case=folder.name):
                self.assertTrue(eval_hosts.case_prompt(folder / "case.yaml").strip())
                for grader in eval_live.read_case(folder / "case.yaml")["graders"]:
                    if grader.get("pattern"):
                        re.compile(str(grader["pattern"]), eval_hosts.regex_flags(str(grader.get("flags") or "")))
                    if grader.get("input_match"):
                        re.compile(str(grader["input_match"]))
                    for key in ("target", "focus"):
                        value = eval_hosts.inline_map(grader.get(key))
                        if isinstance(value, dict):
                            self.assertEqual(value.get("source"), "file", grader)
                            self.assertTrue(value.get("path"), grader)

    def test_prompt_block_is_dedented_and_stops_at_graders(self):
        prompt = eval_hosts.case_prompt(ROOT / "evals" / "live" / "triage-small-task" / "case.yaml")
        self.assertTrue(prompt.startswith("In product/tally: rename"))
        self.assertIn("\n\n(This run is unattended", prompt)
        self.assertNotIn("graders", prompt)

    def test_every_grader_resolves_per_host(self):
        """The mapping note: each grader is local, mapped to a host event, or n/a on that host."""
        table = {}
        for folder in eval_live.case_dirs(ROOT):
            for grader in eval_live.read_case(folder / "case.yaml")["graders"]:
                key = grader["type"] if grader["type"] != "tool_used" else f"tool_used:{grader['tool']}"
                for host, tools in eval_hosts.TOOL_MAP.items():
                    if grader["type"] == "tool_used":
                        how = tools.get(grader["tool"], "n/a")
                        how = "file diff" if how == "diff" else "n/a" if how == "n/a" else "events " + "/".join(how)
                    else:
                        how = "judge (claude -p)" if grader["type"] == "llm" else "local"
                    table.setdefault(key, {})[host] = how
        self.assertEqual(table["regex"], {"codex": "local", "agy": "local"})
        self.assertEqual(table["file_exists"], {"codex": "local", "agy": "local"})
        self.assertEqual(table["tool_used:Write"], {"codex": "file diff", "agy": "file diff"})
        self.assertEqual(table["tool_used:Edit"], {"codex": "file diff", "agy": "file diff"})
        self.assertEqual(table["tool_used:Read"], {"codex": "n/a", "agy": "events read_file/view_file"})
        self.assertEqual(table["tool_used:Agent"], {"codex": "n/a", "agy": "events invoke_subagent"})
        self.assertEqual(table["tool_used:Skill"], {"codex": "n/a", "agy": "n/a"})


class CodexParseTests(unittest.TestCase):
    def setUp(self):
        self.events = eval_hosts.events_of(FIXTURES / "codex-simple-question" / "events.jsonl")

    def test_recorded_run_parses(self):
        answer = (FIXTURES / "codex-simple-question" / "answer.txt").read_text(encoding="utf-8")
        parsed = eval_hosts.parse_codex(self.events, answer)
        self.assertIsNone(parsed["error"])
        self.assertEqual(parsed["final"], answer)
        self.assertGreater(parsed["usage"].get("input_tokens", 0), 0)
        self.assertGreater(parsed["turns"], 0)
        self.assertTrue(all(name == "shell" for name, _ in parsed["tools"]))

    def test_a_run_without_turn_completed_or_an_answer_fails(self):
        cut = [e for e in self.events if e.get("type") != "turn.completed"]
        self.assertEqual(eval_hosts.parse_codex(cut, "answer")["error"], "no turn.completed")
        self.assertEqual(eval_hosts.parse_codex(self.events, "")["error"], "empty -o answer")
        failed = self.events + [{"type": "turn.failed", "error": {"message": "You've hit your usage limit."}}]
        self.assertIn("usage limit", eval_hosts.parse_codex(failed, "answer")["error"])


class AgyParseTests(unittest.TestCase):
    def setUp(self):
        self.events = eval_hosts.events_of(FIXTURES / "agy-simple-question" / "events.jsonl")

    def test_recorded_run_parses(self):
        parsed = eval_hosts.parse_agy(self.events)
        self.assertIsNone(parsed["error"])
        # the last answer step, as Claude's last message; the earlier status lines stay in the trace only
        self.assertTrue(parsed["final"].startswith("In `product/shop`, `apply_discount` rejects negative prices"))
        self.assertNotIn("Triage:", parsed["final"])
        self.assertRegex(parsed["trace"], r"^Triage: small")
        self.assertEqual(parsed["turns"], 9)
        self.assertEqual(parsed["usage"]["total_tokens"], 80876)
        names = [name for name, _ in parsed["tools"]]
        self.assertEqual((names.count("read_file"), names.count("run_command"), names.count("invoke_subagent")),
                         (10, 2, 1))  # each step once, though it streams ACTIVE then DONE or ERROR
        self.assertEqual(parsed["init"]["model"], "gemini-4-hydrogen-xhigh")

    def test_a_run_without_a_good_result_fails(self):
        cut = [e for e in self.events if e.get("event") != "result"]
        self.assertEqual(eval_hosts.parse_agy(cut)["error"], "no result event")
        bad = [{"event": "result", "result": dict(e["result"], status="ERROR", error="quota")}
               if e.get("event") == "result" else e for e in self.events]
        self.assertEqual(eval_hosts.parse_agy(bad)["error"], "result status ERROR: quota")

    def test_a_turn_ended_by_a_permission_request_is_an_error_despite_success(self):
        events = eval_hosts.events_of(FIXTURES / "agy-triage-small-task" / "events.jsonl")
        self.assertEqual(next(e["result"]["status"] for e in events if e.get("event") == "result"), "SUCCESS")
        self.assertEqual(eval_hosts.parse_agy(events)["error"], "stopped on a permission request: read_file")


class GradeTests(TempCase):
    def test_recorded_codex_run_grades_with_na_tools_out_of_the_score(self):
        folder = copy_fixture("codex-simple-question", self.tmp / "run")
        run = eval_hosts.grade_run("codex", case_of("simple-question"), folder)
        verdicts = {g["name"]: g["pass"] for g in run["graders"]}
        self.assertIsNone(verdicts["no-subagent"])  # Agent has no observable event on codex: n/a, not a pass
        self.assertIn("n/a", next(g["explanation"] for g in run["graders"] if g["name"] == "no-subagent"))
        self.assertTrue(verdicts["no-product-edits"])
        self.assertTrue(verdicts["no-checkpoint-for-a-question"])
        self.assertIsNone(run["error"])
        applicable = [g for g in run["graders"] if g["pass"] is not None]
        self.assertEqual(run["score"], round(sum(g["weight"] for g in applicable if g["pass"])
                                             / sum(g["weight"] for g in applicable), 4))
        self.assertEqual(run["costUsd"], 0)

    def test_recorded_agy_run_counts_its_subagent_and_reads(self):
        folder = copy_fixture("agy-simple-question", self.tmp / "run")
        run = eval_hosts.grade_run("agy", case_of("simple-question"), folder)
        verdicts = {g["name"]: g["pass"] for g in run["graders"]}
        self.assertFalse(verdicts["no-subagent"])  # it delegated after its shell was denied: invoke_subagent
        self.assertTrue(verdicts["answers-from-source"] and verdicts["half-up"])
        self.assertEqual((run["score"], run["error"]), (0.8333, None))
        parsed = eval_hosts.parse_agy(eval_hosts.events_of(folder / "events.jsonl"))
        read = {"tool": "Read", "input_match": r"product[\\/]+shop[\\/]+shop[\\/]+pricing\.py"}
        self.assertEqual(eval_hosts.grade_tool_used(read, "agy", parsed, []), (True, "Read called 1x (expected 1..inf)"))

    def test_recorded_agy_permission_stop_is_invalid_not_a_score(self):
        folder = copy_fixture("agy-triage-small-task", self.tmp / "run")
        run = eval_hosts.grade_run("agy", case_of("triage-small-task"), folder)
        self.assertIsNone(run["score"])
        self.assertEqual(run["error"], "stopped on a permission request: read_file")

    def test_diff_maps_new_files_to_write_and_changed_or_deleted_ones_to_edit(self):
        work = self.tmp / "work"
        (work / "product" / "shop" / ".git").mkdir(parents=True)
        (work / "product" / "shop" / "a.py").write_text("a = 1\n", encoding="utf-8")
        (work / "product" / "shop" / "gone.py").write_text("x\n", encoding="utf-8")
        before = eval_hosts.files_of(work)
        (work / "product" / "shop" / "a.py").write_text("a = 2\n", encoding="utf-8")
        (work / "product" / "shop" / "gone.py").unlink()
        (work / ".tinker" / "tasks").mkdir(parents=True)
        (work / ".tinker" / "tasks" / "t.md").write_text("Slice 1\nSlice 2\n", encoding="utf-8")
        (work / "product" / "shop" / ".git" / "index").write_text("ignored", encoding="utf-8")
        events = eval_hosts.changes(work, before)
        self.assertEqual([(e["tool"], e["input"]["file_path"].split("work/")[1]) for e in events],
                         [("Write", ".tinker/tasks/t.md"), ("Edit", "product/shop/a.py"),
                          ("Edit", "product/shop/gone.py")])
        parsed = {"tools": [], "final": "", "trace": ""}
        slices = {"tool": "Write", "input_match": r'"file_path"\s*:\s*"[^"]*\.tinker[\\/]+tasks[\\/]+[^"]*"'
                                                 r'[\s\S]*[Ss]lice\s*1\b[\s\S]*[Ss]lice\s*2\b'}
        self.assertTrue(eval_hosts.grade_tool_used(slices, "agy", parsed, events)[0])
        edits = {"tool": "Edit", "input_match": "product[\\\\/]", "min": 0, "max": 0}
        self.assertEqual(eval_hosts.grade_tool_used(edits, "codex", parsed, events),
                         (False, "Edit called 2x (expected 0..0)"))

    def test_regex_targets_flags_and_match(self):
        work = self.tmp / "work"
        (work / "product").mkdir(parents=True)
        (work / "product" / "f.py").write_text("row_count = 0\nreturn row_count\n", encoding="utf-8")
        parsed = {"final": "It raises ValueError.", "trace": "Triage: **small** · 0 helpers\n...", "tools": []}
        grade = eval_hosts.grade_regex
        self.assertTrue(grade({"pattern": "valueerror", "flags": "i"}, parsed, work)[0])
        self.assertFalse(grade({"pattern": "valueerror"}, parsed, work)[0])
        self.assertTrue(grade({"pattern": r"Triage:\s*[*_`]*\s*small\b", "target": "trace"}, parsed, work)[0])
        self.assertFalse(grade({"pattern": "Triage", "target": "last_message"}, parsed, work)[0])
        self.assertTrue(grade({"pattern": "Triage", "match": "not_contains"}, parsed, work)[0])
        target = "{ source: file, path: product/f.py }"
        self.assertTrue(grade({"pattern": r"row_count = 0[\s\S]*return row_count", "target": target}, parsed, work)[0])
        self.assertEqual(grade({"pattern": "x", "target": "{ source: file, path: product/no.py }"}, parsed, work),
                         (False, "file product/no.py missing"))
        with self.assertRaises(ValueError):
            grade({"pattern": "x", "match": "count:2"}, parsed, work)

    def test_a_case_whose_graders_are_all_na_is_an_error_not_a_score(self):
        folder = copy_fixture("codex-simple-question", self.tmp / "run")
        case = {"graders": [{"name": "only", "type": "tool_used", "tool": "Agent", "min": 0, "max": 0}]}
        run = eval_hosts.grade_run("codex", case, folder)
        self.assertIsNone(run["score"])
        self.assertEqual(run["error"], "every grader is n/a on codex")


class JudgeTests(TempCase):
    def fake_judge(self, replies):
        bin_dir = self.tmp / "judge"
        bin_dir.mkdir()
        (bin_dir / "fake_judge.py").write_text(FAKE_JUDGE, encoding="utf-8")
        (bin_dir / "judge.json").write_text(json.dumps(replies), encoding="utf-8")
        if os.name == "nt":
            exe = bin_dir / "claude.cmd"
            exe.write_text(f'@"{PYTHON}" "%~dp0fake_judge.py" %*\r\n@exit /b %errorlevel%\r\n', encoding="utf-8")
        else:
            exe = bin_dir / "claude"
            exe.write_text(f'#!/bin/sh\nexec "{PYTHON}" "$(dirname "$0")/fake_judge.py" "$@"\n')
            exe.chmod(0o755)
        return str(exe), bin_dir / "judge.log"

    def test_majority_of_three_pinned_votes_without_tools(self):
        claude, log = self.fake_judge(["PASS", "**FAIL**", "pass - it answers no first"])
        verdict, said, cost = eval_hosts.judge(claude, "claude-haiku-5-5", "answers no", "No: it rounds half up.")
        self.assertEqual((verdict, said), ("PASS", ["PASS", "FAIL", "PASS"]))
        self.assertAlmostEqual(cost, 0.003)
        calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(calls), 3)
        args = calls[0]["args"]
        self.assertEqual(args[args.index("--model") + 1], "claude-haiku-5-5")
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("No: it rounds half up.", calls[0]["stdin"])

    def test_an_unreadable_vote_is_a_grader_error(self):
        claude, _ = self.fake_judge(["PASS", "I think it mostly passes", "PASS"])
        self.assertIsNone(eval_hosts.judge(claude, "m", "c", "r")[0])
        folder = copy_fixture("codex-simple-question", self.tmp / "run")
        case = {"graders": [{"name": "judged", "type": "llm", "criteria": "answers"}]}
        run = eval_hosts.grade_run("codex", case, folder, claude, "m")
        self.assertIsNone(run["score"])
        self.assertIn("grader judged", run["error"])


class HostGateTests(TempCase):
    def setUp(self):
        super().setUp()
        write_case(self.tmp, "reg-case", ["review", "regression"])
        write_case(self.tmp, "held-case", ["review", "heldout"])
        self.claude_baseline = self.tmp / "evals" / "live" / "accepted.json"
        self.count = 0

    def result(self, host=None, score=1.0, setup=None):
        self.count += 1
        doc = {"startedAt": "2026-11-25T00:00:00Z", "suite": {"modelOverride": "m", "judgeModel": "j"},
               "cases": [{"name": n, "arms": {"with": [{"score": score, "costUsd": 0, "turns": 3, "error": None}]}}
                         for n in ("reg-case", "held-case")]}
        if host:
            doc.update(host=host, hostVersion="1.0")
        if setup:
            doc["userSetup"] = setup
        path = self.tmp / f"result{self.count}.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def gate(self, path, *extra):
        return self.main("gate", "--result", str(path), *extra, root=self.tmp)

    def test_a_host_result_accepts_into_its_own_file_only(self):
        self.claude_baseline.write_text('{"model": "opus"}\n', encoding="utf-8")
        before = self.claude_baseline.read_bytes()
        code, out = self.gate(self.result("codex"), "--accept")
        self.assertEqual(code, 0, out)
        own = self.tmp / "evals" / "live" / "accepted-codex.json"
        record = json.loads(own.read_text(encoding="utf-8"))
        self.assertEqual((record["host"], record["model"]), ("codex", "m"))
        self.assertEqual(self.claude_baseline.read_bytes(), before)
        code, out = self.gate(self.result("codex", score=0.99))
        self.assertEqual(code, 0, out)
        self.assertIn("reports no cost", out)

    def test_a_changed_user_setup_cannot_pass(self):
        setup = {"~/.gemini/GEMINI.md": "aaa"}
        self.assertEqual(self.gate(self.result("agy", setup=setup), "--accept")[0], 0)
        own = json.loads((self.tmp / "evals" / "live" / "accepted-agy.json").read_text(encoding="utf-8"))
        self.assertEqual(own["userSetup"], setup)
        code, out = self.gate(self.result("agy", setup=setup))
        self.assertEqual(code, 0, out)
        self.assertIn("Not isolated: this agy run also loaded 1 plugins", out)
        code, out = self.gate(self.result("agy", setup={"~/.gemini/GEMINI.md": "bbb"}))
        self.assertEqual(code, 1, out)
        self.assertIn("setup changed since the baseline (~/.gemini/GEMINI.md)", out)

    def test_never_compares_or_accepts_across_hosts(self):
        self.gate(self.result("codex"), "--accept")
        codex_file = self.tmp / "evals" / "live" / "accepted-codex.json"
        before = codex_file.read_bytes()
        for result, extra in ((self.result(), ("--accepted", str(codex_file))),
                              (self.result("agy"), ("--accepted", str(codex_file)))):
            code, out = self.gate(result, *extra, "--accept")
            self.assertEqual(code, 2, out)
            self.assertIn("hosts are never compared", out)
        self.assertEqual(codex_file.read_bytes(), before)

    def test_a_host_result_never_touches_the_claude_baseline(self):
        self.claude_baseline.write_text('{"model": "opus"}\n', encoding="utf-8")
        before = self.claude_baseline.read_bytes()
        code, out = self.gate(self.result("agy"), "--accepted", str(self.claude_baseline), "--accept")
        self.assertEqual(code, 2, out)
        self.assertIn("never compared with or accepted into the claude baseline", out)
        self.assertEqual(self.claude_baseline.read_bytes(), before)

    def test_claude_record_keeps_its_shape(self):
        code, out = self.gate(self.result(), "--accept")
        self.assertEqual(code, 0, out)
        self.assertNotIn("host", json.loads(self.claude_baseline.read_text(encoding="utf-8")))


class HostRunTests(TempCase):
    def test_refusals_before_any_run(self):
        write_case(self.tmp, "alpha", ["review", "regression"])
        for argv, message in ((("--adaptive",), "claude host only"), (("--ablation", "with-without"), "claude host only")):
            with mock.patch("shutil.which", return_value="x"):
                code, out = self.main("run", "--host", "codex", *argv, root=self.tmp)
            self.assertEqual(code, 1)
            self.assertIn(message, out)
        code, out = self.main("run", "--effort", "high", root=self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("--effort is for --host codex or agy", out)

    def test_host_defaults(self):
        args = eval_live.parser().parse_args(["run", "--host", "codex"])
        self.assertIsNone(args.model)
        work, folder = self.tmp / "w", self.tmp / "f"
        args.effort, args.timeout = None, 60
        command, stdin = eval_hosts.host_command("codex", "codex", args, work, "hi", folder)
        self.assertNotIn("-m", command)
        for flag in ("--ignore-user-config", "--skip-git-repo-check", "--json", "--ephemeral", "approval_policy=never"):
            self.assertIn(flag, command)
        self.assertEqual((command[-1], stdin), ("-", "hi"))
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        code_args = eval_live.parser().parse_args(["run", "--host", "agy"])
        with mock.patch.object(eval_live, "run", return_value=0) as run:
            eval_live.main(["run", "--host", "agy"], root=self.tmp)
        resolved = run.call_args[0][0]
        self.assertEqual((resolved.model, resolved.effort), ("gemini-4-hydrogen-xhigh", "xhigh"))
        self.assertIsNone(code_args.model)
        command, stdin = eval_hosts.host_command("agy", "agy", resolved, work, "hi", folder)
        self.assertEqual(command[command.index("--model") + 1], "gemini-4-hydrogen-xhigh")
        self.assertEqual(command[command.index("--effort") + 1], "xhigh")
        self.assertEqual(command[command.index("--mode") + 1], "accept-edits")
        self.assertIn("--disable-slash-commands", command)
        self.assertEqual(command[command.index("--log-file") + 1], str(folder / "agy.log"))
        self.assertNotIn("--dangerously-skip-permissions", command)
        self.assertIsNone(stdin)


class UserSetupTests(TempCase):
    def test_records_what_each_host_loads_beside_the_snapshot(self):
        home = self.tmp / "home"
        plugin = ".gemini/config/plugins/example"
        files = {".gemini/GEMINI.md": "rules", f"{plugin}/plugin.json": "{}", ".codex/AGENTS.md": "",
                 ".codex/skills/one/SKILL.md": "s"}
        for rel, text in files.items():
            (home / rel).parent.mkdir(parents=True, exist_ok=True)
            (home / rel).write_text(text, encoding="utf-8")
        (home / ".agents" / "skills" / "empty").mkdir(parents=True)
        with mock.patch.object(Path, "home", return_value=home), mock.patch.dict(os.environ, {"CODEX_HOME": ""}):
            agy, codex = eval_hosts.user_setup("agy"), eval_hosts.user_setup("codex")
            self.assertEqual(sorted(agy), ["~/.gemini/GEMINI.md", f"~/{plugin}"])
            self.assertEqual(sorted(codex), ["~/.codex/skills/one"])  # an empty file or folder loads nothing
            (home / ".gemini/GEMINI.md").write_text("other rules", encoding="utf-8")
            self.assertNotEqual(eval_hosts.user_setup("agy")["~/.gemini/GEMINI.md"], agy["~/.gemini/GEMINI.md"])


class FingerprintHostTests(TempCase):
    def test_host_baselines_stay_out_of_the_fingerprint_and_the_bundle(self):
        tree = self.tmp / "tree"
        (tree / "evals" / "live").mkdir(parents=True)
        (tree / "AGENTS.md").write_text("x\n", encoding="utf-8")
        first = eval_live.tree_fingerprint(tree)
        (tree / "evals" / "live" / "accepted-codex.json").write_text("{}\n", encoding="utf-8")
        self.assertEqual(eval_live.tree_fingerprint(tree), first)
        (tree / "evals" / "live" / "accepted-codex.json.bak").write_text("{}\n", encoding="utf-8")
        self.assertNotEqual(eval_live.tree_fingerprint(tree), first)


if __name__ == "__main__":
    unittest.main()
