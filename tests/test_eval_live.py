"""Live eval runner and gate tests: a fake `claude` on PATH stands in for the host, so no test spends model usage.

These prove the runner's bookkeeping (run count, usage refusal, snapshot, bundle, result copy), the gate's verdicts
and the cases' structure, and that every scaffold builds its workspace; they do not run a case against a model.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import eval_live  # noqa: E402

PYTHON = getattr(sys, "_base_executable", sys.executable)
LIVE = ROOT / "evals" / "live"
GRADER_TYPES = {"file_exists", "regex", "tool_used", "llm"}
CASE_TOOLS = {"Read", "Grep", "Glob", "Write", "Edit", "Skill", "Agent"}
FAKE_CLAUDE = r'''
import json, os, sys
from pathlib import Path
here = Path(__file__).resolve().parent
config = json.loads((here / "fake.json").read_text(encoding="utf-8"))
args = sys.argv[1:]
with open(here / "calls.log", "a", encoding="utf-8") as log:
    log.write(json.dumps({"args": args, "cwd": os.getcwd()}) + "\n")
if args[:1] == ["-p"]:
    print(json.dumps({"type": "system", "subtype": "init"}))
    if config.get("usage") is not None:
        print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"unifiedWindows": {
            "five_hour": {"utilization": config["usage"], "resetsAt": 1760000000}}}}))
    print("not json")
    sys.exit(0)
if args[:2] == ["plugin", "eval"]:
    result = Path(args[args.index("--json") + 1])
    doc = {"startedAt": "2026-10-19T00:00:00Z", "suite": {"modelOverride": "opus"}, "costUsd": 0.5,
           "cases": config.get("cases") or []}
    if config.get("rerun_score") is not None and "--case" in args and "--runs" in args:  # an --adaptive re-run
        runs = int(args[args.index("--runs") + 1])
        run = {"score": config["rerun_score"], "costUsd": 0.1, "turns": 3}
        doc = {"costUsd": 0.1 * runs, "cases": [{"name": args[args.index("--case") + 1], "arms": {"with": [run] * runs}}]}
    result.write_text(json.dumps(doc), encoding="utf-8")
sys.exit(config.get("exit", 0))
'''


def write_case(root, name, tags, runs=None, graders=1):
    folder = Path(root) / "evals" / "live" / name
    folder.mkdir(parents=True, exist_ok=True)
    lines = ['schema_version: "1.1"', f"name: {name}", "description: test case", f"tags: [{', '.join(tags)}]"]
    if runs:
        lines.append(f"runs: {runs}")
    lines += ["context:", "  scaffold_script: setup.sh", "execution:", "  append_system_prompt: TINKER_AGENTS_MD",
              "  max_turns: 5", "  allowed_tools: [Read]", "  prompt: |", "    hello", "graders:"]
    for i in range(graders):
        lines += [f"  - name: g{i}", "    type: regex", "    pattern: 'x'"]
    (folder / "case.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (folder / "setup.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    return folder


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tinker_evaltest_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def fake_claude(self, usage=None, exit_code=0, cases=None, rerun_score=None):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "fake_claude.py").write_text(FAKE_CLAUDE, encoding="utf-8")
        (bin_dir / "fake.json").write_text(json.dumps({"usage": usage, "exit": exit_code, "cases": cases,
                                                       "rerun_score": rerun_score}), encoding="utf-8")
        if os.name == "nt":
            (bin_dir / "claude.cmd").write_text(f'@"{PYTHON}" "%~dp0fake_claude.py" %*\r\n'
                                                "@exit /b %errorlevel%\r\n", encoding="utf-8")
        else:
            script = bin_dir / "claude"
            script.write_text(f'#!/bin/sh\nexec "{PYTHON}" "$(dirname "$0")/fake_claude.py" "$@"\n')
            script.chmod(0o755)
        patcher = mock.patch.dict(os.environ, {"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")})
        patcher.start()
        self.addCleanup(patcher.stop)
        return bin_dir / "calls.log"

    @staticmethod
    def calls(log):
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []

    def main(self, *argv, root, temp=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = eval_live.main(list(argv), root=root, temp=temp)
        return code, out.getvalue() + err.getvalue()


class RunCountTests(TempCase):
    def test_counts_cases_runs_and_arms(self):
        write_case(self.tmp, "alpha", ["review", "regression"])
        write_case(self.tmp, "beta", ["story", "regression"], runs=3)
        write_case(self.tmp, "gamma", ["review", "heldout"])
        (self.tmp / "evals" / "live" / "_shared").mkdir()
        count = eval_live.count_runs
        self.assertEqual(count(self.tmp), 5)  # 1 + 3 + 1: one run per case unless it says runs:
        self.assertEqual(count(self.tmp, runs=2), 6)
        self.assertEqual(count(self.tmp, ablation="with-without"), 10)
        self.assertEqual(count(self.tmp, tags=["review"]), 2)
        self.assertEqual(count(self.tmp, tags=["heldout", "story"]), 4)
        self.assertEqual(count(self.tmp, case_glob="b*"), 3)
        self.assertEqual(count(self.tmp, case_glob="none*"), 0)


class UsageCheckTests(TempCase):
    """Above 20 agent runs the runner probes the five-hour window first; the probe fails closed."""

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "checkout"
        write_case(self.root, "alpha", ["regression"])
        self.prereqs = mock.patch.object(eval_live, "scaffold_env", side_effect=eval_live.EvalError("stop here"))
        self.prereqs.start()  # stop right after the usage decision: these tests never build a run
        self.addCleanup(self.prereqs.stop)

    def outcome(self, *argv, usage):
        log = self.fake_claude(usage=usage)
        log.unlink(missing_ok=True)
        code, out = self.main("run", *argv, root=self.root)
        calls = self.calls(log)
        return code, out, any(c["args"][:1] == ["-p"] for c in calls), "stop here" in out

    def test_refuses_when_the_runs_would_not_fit(self):
        code, out, probed, went_on = self.outcome("--runs", "60", usage=0.9)
        self.assertEqual(code, 1)
        self.assertTrue(probed)
        self.assertFalse(went_on)
        self.assertIn("Not starting 60 eval runs", out)
        self.assertIn("--force", out)
        self.assertRegex(out, r"resets at \d\d:\d\d")

    def test_proceeds_when_the_runs_fit(self):
        code, out, probed, went_on = self.outcome("--runs", "30", usage=0.1)
        self.assertTrue(probed)
        self.assertTrue(went_on)
        self.assertIn("10% used, this run needs ~12% (30 runs)", out)

    def test_unreadable_usage_refuses_unless_forced(self):
        code, out, probed, went_on = self.outcome("--runs", "30", usage=None)
        self.assertEqual(code, 1)
        self.assertFalse(went_on)
        self.assertIn("Could not read the five-hour usage", out)
        code, out, probed, went_on = self.outcome("--runs", "30", "--force", usage=None)
        self.assertFalse(probed)
        self.assertTrue(went_on)

    def test_small_runs_skip_the_probe(self):
        code, out, probed, went_on = self.outcome("--runs", "20", usage=0.99)
        self.assertFalse(probed)
        self.assertTrue(went_on)


class SnapshotTests(TempCase):
    def test_copies_tracked_and_untracked_files_but_never_ignored_ones(self):
        repo = self.tmp / "repo"
        (repo / ".tinker").mkdir(parents=True)
        git(repo, "init", "-q")
        (repo / ".gitignore").write_text(".tinker/\n*.log\n", encoding="utf-8")
        (repo / "tracked.txt").write_text("t", encoding="utf-8")
        (repo / "gone.txt").write_text("g", encoding="utf-8")
        git(repo, "add", "-A")
        (repo / "gone.txt").unlink()  # tracked, deleted from the working tree
        (repo / "new.txt").write_text("n", encoding="utf-8")
        (repo / ".tinker" / "secret.md").write_text("s", encoding="utf-8")
        (repo / "debug.log").write_text("l", encoding="utf-8")
        dest = self.tmp / "copy"
        eval_live.snapshot(repo, dest)
        names = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
        self.assertEqual(names, [".gitignore", "new.txt", "tracked.txt"])

    def test_refuses_a_folder_outside_git(self):
        with self.assertRaises(eval_live.EvalError):
            eval_live.snapshot(self.tmp, self.tmp / "copy")


class RunTests(TempCase):
    """A whole run against a copy of this checkout, with the fake claude in place of the host."""

    def setUp(self):
        super().setUp()
        self.checkout = self.tmp / "checkout"
        eval_live.snapshot(ROOT, self.checkout)
        git(self.checkout, "init", "-q")
        (self.checkout / ".tinker").mkdir(exist_ok=True)
        (self.checkout / ".tinker" / "private.md").write_text("never copied", encoding="utf-8")
        self.runs = self.tmp / "runs"
        self.runs.mkdir()

    def test_run_renders_a_snapshot_bundle_and_keeps_the_result(self):
        log = self.fake_claude()
        code, out = self.main("run", "--case", "playbook-gate", root=self.checkout, temp=self.runs)
        self.assertEqual(code, 0, out)
        (run_dir,) = list(self.runs.iterdir())
        tree, bundle = run_dir / "tinker", run_dir / "home" / ".tinker" / "plugin"
        (call,) = [c for c in self.calls(log) if c["args"][:2] == ["plugin", "eval"]]
        args = call["args"]
        self.assertEqual(Path(call["cwd"]).resolve(), bundle.resolve())
        for flag, value in (("--model", "opus"), ("--concurrency", "4"), ("--ablation", "none"),
                            ("--eval-dir", "evals"), ("--case", "playbook-gate")):
            self.assertEqual(args[args.index(flag) + 1], value, flag)
        for flag in ("--scaffold", "--trust-plugin", "--no-publish"):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index("--allow-tools") + 1:args.index("--allow-tools") + 3], ["Write", "Edit"])
        self.assertNotIn("--runs", args)
        # The snapshot leaves ignored files behind; the bundle has no hooks and carries the filled-in cases.
        self.assertTrue((tree / "AGENTS.md").is_file())
        self.assertFalse((tree / ".tinker").exists())
        self.assertFalse((bundle / "hooks").exists())
        manifest = json.loads((bundle / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "tinker")
        self.assertNotIn("hooks", manifest)
        self.assertTrue((bundle / "skills" / "tinker-implement" / "SKILL.md").is_file())
        roles = {p.stem for p in (tree / "roles").glob("*.md")}  # one agent per role charter
        self.assertEqual({p.stem for p in (bundle / "agents").glob("*.md")}, roles)
        case = (bundle / "evals" / "playbook-gate" / "case.yaml").read_text(encoding="utf-8")
        self.assertNotIn("TINKER_AGENTS_MD", case)
        self.assertIn("    You are the Lead", case)
        self.assertIn(eval_live.ROOT_NOTE, case)
        self.assertRegex(case, r"(?m)^name: playbook-gate\nruns: 1$")
        self.assertEqual((bundle / "evals" / "_shared" / "root.txt").read_text(encoding="utf-8").strip(),
                         tree.as_posix())
        self.assertFalse((bundle / "evals" / "results").exists())
        # The result is copied back into the checkout's ignored results folder.
        (kept,) = list((self.checkout / "evals" / "live" / "results").glob("*.json"))
        self.assertEqual(kept.stem, run_dir.name.removeprefix("tinker_eval_"))
        self.assertIn(f"Result: {kept}", out)

    def test_options_pass_through_and_a_failed_eval_keeps_its_exit_code(self):
        log = self.fake_claude(exit_code=1)
        code, out = self.main("run", "--tag", "heldout", "review", "--runs", "2", "--model", "sonnet", "-j", "1",
                              "--ablation", "with-without", "--force", root=self.checkout, temp=self.runs)
        self.assertEqual(code, 1)
        (call,) = [c for c in self.calls(log) if c["args"][:2] == ["plugin", "eval"]]
        args = call["args"]
        self.assertEqual(args[args.index("--tag") + 1:args.index("--tag") + 3], ["heldout", "review"])
        for flag, value in (("--model", "sonnet"), ("--concurrency", "1"), ("--ablation", "with-without"),
                            ("--runs", "2")):
            self.assertEqual(args[args.index(flag) + 1], value, flag)
        self.assertNotIn("--case", args)
        self.assertEqual(len(list((self.checkout / "evals" / "live" / "results").glob("*.json"))), 1)

    def test_adaptive_reruns_only_complete_cases_that_fell_short_and_merges_them(self):
        def case(name, score, error=None):
            return {"name": name, "arms": {"with": [{"score": score, "costUsd": 0.2, "turns": 0 if error else 3,
                                                     "error": error}]}}
        log = self.fake_claude(cases=[case("alpha", 1.0), case("beta", 0.5), case("gamma", 0, "timed out")],
                               rerun_score=1.0)
        code, out = self.main("run", "--adaptive", "--force", "--ablation", "with-without", root=self.checkout,
                              temp=self.runs)
        self.assertEqual(code, 0, out)
        first, again = [c["args"] for c in self.calls(log) if c["args"][:2] == ["plugin", "eval"]]
        self.assertNotIn("--case", first)
        for flag, value in (("--case", "beta"), ("--runs", "2"), ("--ablation", "none")):
            self.assertEqual(again[again.index(flag) + 1], value, flag)
        self.assertIn("1 case(s) fell short", out)
        (kept,) = list((self.checkout / "evals" / "live" / "results").glob("*.json"))
        doc = json.loads(kept.read_text(encoding="utf-8"))
        self.assertTrue(doc["adaptive"])
        self.assertEqual(doc["mergedFrom"], ["rerun-beta.json"])
        self.assertEqual({c["name"]: len(c["arms"]["with"]) for c in doc["cases"]}, {"alpha": 1, "beta": 3, "gamma": 1})
        self.assertEqual(doc["costUsd"], 0.7)

    def test_no_matching_case_starts_nothing(self):
        log = self.fake_claude()
        code, out = self.main("run", "--case", "no-such-case", root=self.checkout, temp=self.runs)
        self.assertEqual(code, 1)
        self.assertIn("No case matches", out)
        self.assertEqual(self.calls(log), [])
        self.assertEqual(list(self.runs.iterdir()), [])


class GateTests(TempCase):
    def setUp(self):
        super().setUp()
        write_case(self.tmp, "reg-case", ["review", "regression"])
        write_case(self.tmp, "held-case", ["review", "heldout"])
        self.accepted = self.tmp / "accepted.json"
        self.count = 0

    def result(self, score=1.0, cost=0.2, error=None, model="opus", cases=("reg-case", "held-case")):
        self.count += 1
        def r(s, c, e):
            return {"score": s, "costUsd": c, "turns": 0 if e else 5, "error": e}
        doc = {"startedAt": "2026-10-19T00:00:00Z", "suite": {"modelOverride": model},
               "cases": [{"name": name, "arms": {"with": [r(score, cost, error), r(score, cost, None)]}}
                         for name in cases]}
        path = self.tmp / f"result{self.count}.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def gate(self, path, *extra):
        return self.main("gate", "--result", str(path), "--accepted", str(self.accepted), *extra, root=self.tmp)

    def test_no_baseline_fails_until_accepted(self):
        code, out = self.gate(self.result())
        self.assertEqual(code, 1)
        self.assertIn("no baseline", out)
        self.assertFalse(self.accepted.exists())
        code, out = self.gate(self.result(), "--accept")
        self.assertEqual(code, 0, out)
        record = json.loads(self.accepted.read_text(encoding="utf-8"))
        self.assertEqual(record["model"], "opus")
        self.assertEqual(record["sets"]["regression"], {"score": 1.0, "costPerRunUsd": 0.2, "runs": 2})
        self.assertEqual(record["sets"]["heldout"]["runs"], 2)
        self.assertEqual(record["result"], "result2.json")
        self.assertIn("commit", record)

    def test_pass_and_regressions(self):
        self.gate(self.result(), "--accept")
        code, out = self.gate(self.result(score=0.99, cost=0.21))  # within the noise tolerances
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("| pass |"), 2)
        code, out = self.gate(self.result(score=0.5))
        self.assertEqual(code, 1)
        self.assertIn("FAIL: score", out)
        code, out = self.gate(self.result(cost=0.4))
        self.assertEqual(code, 1)
        self.assertIn("FAIL: cost", out)

    def test_errored_runs_are_invalid_and_cannot_be_accepted(self):
        code, out = self.gate(self.result(error="rate limited"), "--accept")
        self.assertEqual(code, 2)
        self.assertIn("INVALID", out)
        self.assertFalse(self.accepted.exists())

    def test_unknown_case_and_unreadable_result_are_invalid(self):
        code, out = self.gate(self.result(cases=("missing-case",)))
        self.assertEqual(code, 2)
        self.assertIn("missing-case", out)
        bad = self.tmp / "bad.json"
        bad.write_text("{", encoding="utf-8")
        self.assertEqual(self.gate(bad)[0], 2)

    def test_another_model_never_passes_but_can_be_accepted(self):
        self.gate(self.result(), "--accept")
        code, out = self.gate(self.result(model="sonnet"))
        self.assertEqual(code, 1)
        self.assertIn("new model", out)
        self.assertIn("opus -> sonnet", out)
        code, out = self.gate(self.result(model="sonnet", cases=("reg-case",)), "--accept")
        self.assertEqual(code, 0)
        record = json.loads(self.accepted.read_text(encoding="utf-8"))
        self.assertEqual(record["model"], "sonnet")
        self.assertEqual(set(record["sets"]), {"regression"})  # the other model's sets are not comparable

    def test_sets_average_per_case_so_reruns_do_not_weigh_more(self):
        write_case(self.tmp, "reg-two", ["review", "regression"])
        def runs(*scores):
            return [{"score": s, "costUsd": 0.1 if len(scores) == 1 else 0.3, "turns": 5} for s in scores]
        path = self.tmp / "mixed.json"
        path.write_text(json.dumps({"suite": {"modelOverride": "opus"}, "cases": [
            {"name": "reg-case", "arms": {"with": runs(1.0)}},
            {"name": "reg-two", "arms": {"with": runs(0.0, 1.0, 1.0)}}]}), encoding="utf-8")
        summary, errored = eval_live.summarize(json.loads(path.read_text(encoding="utf-8")), self.tmp)
        self.assertEqual(errored, [])
        self.assertEqual(summary["regression"], {"score": 0.833, "costPerRunUsd": 0.2, "runs": 4})

    def test_an_adaptive_result_never_passes_against_a_plain_baseline(self):
        self.gate(self.result(), "--accept")
        path = self.result()
        doc = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**doc, "adaptive": True}), encoding="utf-8")
        code, out = self.gate(path)
        self.assertEqual(code, 1)
        self.assertIn("new mode", out)
        self.assertIn("off -> on", out)
        self.assertEqual(self.gate(path, "--accept")[0], 0)
        self.assertTrue(json.loads(self.accepted.read_text(encoding="utf-8"))["adaptive"])
        self.assertEqual(self.gate(path)[0], 0)

    def test_accept_keeps_sets_the_result_did_not_cover(self):
        self.gate(self.result(), "--accept")
        self.gate(self.result(score=0.9, cases=("reg-case",)), "--accept")
        record = json.loads(self.accepted.read_text(encoding="utf-8"))
        self.assertEqual(record["sets"]["regression"]["score"], 0.9)
        self.assertEqual(record["sets"]["heldout"]["score"], 1.0)


class CaseStructureTests(unittest.TestCase):
    """Every live case is well formed; these check structure, not behavior."""

    def test_every_case_is_well_formed(self):
        folders = eval_live.case_dirs(ROOT)
        self.assertGreaterEqual(len(folders), 15)
        sets = {"regression": 0, "heldout": 0}
        for folder in folders:
            with self.subTest(case=folder.name):
                case = eval_live.read_case(folder / "case.yaml")
                text = (folder / "case.yaml").read_text(encoding="utf-8")
                self.assertEqual(case.get("name"), folder.name)
                tags = case.get("tags") or []
                self.assertEqual(len({"regression", "heldout"} & set(tags)), 1, tags)
                sets[eval_live.case_set(case)] += 1
                self.assertTrue(case.get("description"))
                self.assertEqual(case["context"].get("scaffold_script"), "setup.sh")
                self.assertIn(eval_live.PLACEHOLDER + "\n", text)
                self.assertRegex(text, r"(?m)^  prompt: \|\n    \S")
                self.assertTrue(set(case["execution"]["allowed_tools"]) <= CASE_TOOLS, "no shell tools on Windows")
                self.assertTrue(case["graders"])
                names = [g.get("name") for g in case["graders"]]
                self.assertEqual(len(names), len(set(names)))
                for grader in case["graders"]:
                    self.assertIn(grader.get("type"), GRADER_TYPES, grader)
                    key = {"regex": "pattern", "llm": "criteria", "tool_used": "tool", "file_exists": "path"}
                    self.assertTrue(grader.get(key[grader["type"]]), grader)
                self.assertLessEqual(sum(g["type"] == "llm" for g in case["graders"]), 2, "llm graders sparingly")
                setup = (folder / "setup.sh").read_text(encoding="utf-8")
                self.assertTrue(setup.startswith("#!/usr/bin/env bash\n"))
                self.assertIn('. "$(dirname "$0")/../_shared/workspace.sh"', setup)
        self.assertGreaterEqual(sets["heldout"], 3)
        self.assertGreater(sets["regression"], sets["heldout"])

    def test_cases_stay_generic(self):
        # Fixtures are tiny invented repositories; cases name no real project, organisation or tracker.
        for path in LIVE.rglob("*"):
            if path.is_file() and path.suffix in (".yaml", ".sh"):
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"\b[A-Z]:[\\/]|/Users/|/home/\w+/|(?i:azure devops|\bado\b|jira)", path)

    def test_results_are_ignored_and_no_root_pointer_is_tracked(self):
        self.assertIn("/evals/live/results/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
        self.assertFalse((LIVE / "_shared" / "root.txt").exists())


@unittest.skipUnless(shutil.which("git"), "git is not on PATH")
class ScaffoldTests(TempCase):
    """Each scaffold builds a Tinker-root workspace with committed fixture repositories (needs bash and git)."""

    def test_every_scaffold_builds_its_workspace(self):
        try:
            env = eval_live.scaffold_env()
        except eval_live.EvalError as error:
            self.skipTest(str(error))
        tree = self.tmp / "tinker"
        eval_live.snapshot(ROOT, tree)
        bundle = eval_live.render_bundle(tree, self.tmp / "home")
        for folder in eval_live.case_dirs(ROOT):
            with self.subTest(case=folder.name):
                work = self.tmp / "work" / folder.name
                work.mkdir(parents=True)
                script = (bundle / "evals" / folder.name / "setup.sh").as_posix()
                bash = shutil.which("bash", path=env["PATH"])
                proc = subprocess.run([bash, script], cwd=work, env=env, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue((work / "AGENTS.md").is_file())
                self.assertTrue((work / ".agents" / "skills" / "tinker-implement" / "SKILL.md").is_file())
                self.assertTrue((work / ".tinker" / "retros").is_dir())
                repos = [p for p in (work / "product").iterdir() if p.is_dir()]
                self.assertTrue(repos)
                for repo in repos:
                    status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                            capture_output=True, text=True)
                    self.assertEqual(status.stdout, "", f"{repo.name} has uncommitted fixture files")
                    self.assertFalse((repo / ".tinker").exists())
                # Regex graders that read a file name one the scaffold created.
                text = (folder / "case.yaml").read_text(encoding="utf-8")
                for target in re.findall(r"target: \{ source: file, path: ([^ }]+) \}", text):
                    self.assertTrue((work / target).is_file(), target)


if __name__ == "__main__":
    unittest.main()
