"""Suite acceptance over synthetic fixture records: these test the tooling, never live host behaviour."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Changing a held-out case changes this digest. Update it only as a deliberate, reviewed decision about
# the held-out expectations, never to make a change pass.
HELD_OUT_SHA256 = "67d87833a226c3b89036ec8760b727a12dd92e8a25a7a94d40b0ba3526dbee2c"


class SuiteCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.suite = importlib.import_module("evals.suite")
        case = {"prompt": "p", "setup": "s", "manual_review": "m"}
        self.cases = [
            dict(case, id="alpha", set="regression", rules=[{"field": "tests_run", "op": "gte", "value": 1}]),
            dict(case, id="beta", set="regression", hosts=["codex"],
                 rules=[{"field": "claimed_success", "op": "eq", "value": False}]),
            dict(case, id="gamma", set="held-out", rules=[{"field": "tests_run", "op": "gte", "value": 1}]),
        ]
        self.catalog = self.base / "cases.json"
        self.catalog.write_text(json.dumps(self.cases), encoding="utf-8")
        self.manifest = {"set": "regression", "acceptance": "live", "configuration": "disposable fixture v1",
                         "hosts": {"claude": {"version": "2.1", "model": "m1"}, "codex": {"version": "0.1", "model": "m2"}},
                         "runs": [self.make_run("claude", "alpha"), self.make_run("codex", "alpha"), self.make_run("codex", "beta")]}

    def make_run(self, host, case, origin="observed", value=None, review=True, runs="runs"):
        folder = self.base / runs / host / case
        folder.mkdir(parents=True, exist_ok=True)
        trace = f"{host} {case} synthetic trace\nobserved line\n".encode("utf-8")
        (folder / "trace.txt").write_bytes(trace)
        rule = next(c for c in self.cases if c["id"] == case)["rules"][0]
        record = {"case_id": case, "origin": origin,
                  "source": {"path": "trace.txt", "sha256": hashlib.sha256(trace).hexdigest()},
                  "observations": {rule["field"]: {"value": rule["value"] if value is None else value, "lines": [2, 2]}}}
        (folder / "record.json").write_text(json.dumps(record), encoding="utf-8")
        run = {"host": host, "case": case, "record": f"{runs}/{host}/{case}/record.json"}
        if review:
            run["review"] = {"reviewer": "R. Viewer", "date": "2026-09-26", "complete": True}
        return run

    def evaluate(self, manifest=None, name="suite.json"):
        path = self.base / name
        path.write_text(json.dumps(self.manifest if manifest is None else manifest), encoding="utf-8")
        return self.suite.evaluate(path, self.catalog)

    def problems(self, result):
        return "\n".join(result.get("problems", []))

    def test_complete_observed_and_reviewed_runs_are_accepted(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "accepted", self.problems(result))
        self.assertEqual({(r["host"], r["case"], r["verdict"]) for r in result["runs"]},
                         {("claude", "alpha", "accepted"), ("codex", "alpha", "accepted"), ("codex", "beta", "accepted")})

    def test_expected_coverage_comes_from_the_catalog_not_the_runs(self):
        self.manifest["runs"] = [r for r in self.manifest["runs"] if (r["host"], r["case"]) != ("codex", "beta")]
        result = self.evaluate()
        self.assertEqual(result["status"], "not-verified")
        self.assertIn("missing run for codex/beta", self.problems(result))
        self.assertNotIn("claude/beta", self.problems(result))  # beta applies to Codex only

    def test_duplicate_unknown_and_undeclared_runs_are_invalid(self):
        broken = [
            lambda m: m["runs"].append(copy.deepcopy(m["runs"][0])),
            lambda m: m["runs"].append({"host": "claude", "case": "gamma", "record": "runs/claude/alpha/record.json"}),
            lambda m: m["runs"].append({"host": "claude", "case": "beta", "record": "runs/codex/beta/record.json"}),
            lambda m: m["runs"].append({"host": "claude", "case": "delta", "record": "runs/claude/alpha/record.json"}),
            lambda m: m["runs"].append({"host": "antigravity", "case": "alpha", "record": "runs/claude/alpha/record.json"}),
            lambda m: m["runs"][0].update(record="../outside.json"),
            lambda m: m.update(acceptance="probably"),
            lambda m: m.update(extra=True),
        ]
        for index, damage in enumerate(broken):
            manifest = copy.deepcopy(self.manifest)
            damage(manifest)
            with self.subTest(index=index):
                self.assertEqual(self.evaluate(manifest)["status"], "invalid")

    def test_failed_checks_and_malformed_evidence_are_rejected(self):
        self.manifest["runs"][0] = self.make_run("claude", "alpha", value=0)
        result = self.evaluate()
        self.assertEqual(result["status"], "rejected")
        self.manifest["runs"][0] = self.make_run("claude", "alpha")
        (self.base / "runs" / "claude" / "alpha" / "trace.txt").write_bytes(b"edited after its digest\n")
        result = self.evaluate()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(next(r for r in result["runs"] if r["host"] == "claude")["machine"], "invalid")

    def test_synthetic_records_cannot_establish_live_acceptance(self):
        self.manifest["runs"][0] = self.make_run("claude", "alpha", origin="synthetic")
        result = self.evaluate()
        self.assertEqual(result["status"], "rejected")
        self.assertIn("synthetic", self.problems(result))
        self.manifest["acceptance"] = "fixture"  # a tooling check may use fixtures, and says so
        self.assertEqual(self.evaluate()["status"], "accepted")

    def test_acceptance_requires_complete_human_review(self):
        for review in (None, {"reviewer": "R. Viewer", "date": "2026-09-26", "complete": False}):
            manifest = copy.deepcopy(self.manifest)
            if review is None:
                del manifest["runs"][0]["review"]
            else:
                manifest["runs"][0]["review"] = review
            with self.subTest(review=review):
                result = self.evaluate(manifest)
                self.assertEqual(result["status"], "not-verified")
                claude = next(r for r in result["runs"] if r["host"] == "claude")
                self.assertEqual((claude["machine"], claude["verdict"]), ("passed", "not-verified"))

    def test_metrics_are_reported_only_as_measured(self):
        self.manifest["runs"][0]["metrics"] = {"duration_seconds": {"value": 42, "source": "trace.txt line 1"}}
        result = self.evaluate()
        runs = {(r["host"], r["case"]): r for r in result["runs"]}
        self.assertEqual(runs[("claude", "alpha")]["metrics"], {"duration_seconds": {"value": 42, "source": "trace.txt line 1"}})
        self.assertEqual(runs[("codex", "alpha")]["metrics"], "unavailable")
        for metric in ({"value": 42}, {"value": -1, "source": "x"}, {"value": True, "source": "x"}):
            manifest = copy.deepcopy(self.manifest)
            manifest["runs"][0]["metrics"] = {"tokens": metric}
            with self.subTest(metric=metric):
                self.assertEqual(self.evaluate(manifest)["status"], "invalid")

    def test_compare_needs_comparable_runs_and_reports_case_level_changes(self):
        before = self.base / "before.json"
        before.write_text(json.dumps(self.manifest), encoding="utf-8")
        after = copy.deepcopy(self.manifest)
        after["runs"][2] = self.make_run("codex", "beta", value=True, runs="after-runs")
        after["hosts"]["codex"]["version"] = "0.2"
        result = self.suite.compare(before, self.write(after, "after.json"), self.catalog)
        self.assertTrue(result["comparable"], result)
        self.assertEqual(result["changes"], [{"host": "codex", "case": "beta", "before": "accepted", "after": "rejected"}])
        self.assertIn("codex version", " ".join(result["notes"]))
        self.assertNotIn("score", json.dumps(result))
        for change in ({"configuration": "another setup"}, {"acceptance": "fixture"},
                       {"hosts": {"claude": {"version": "2.1", "model": "other"}, "codex": {"version": "0.1", "model": "m2"}}}):
            with self.subTest(change=change):
                result = self.suite.compare(before, self.write(dict(self.manifest, **change), "other.json"), self.catalog)
                self.assertFalse(result["comparable"])
        edited = copy.deepcopy(self.cases)
        edited[0]["rules"][0]["value"] = 0  # a weakened case definition is not the same evaluation
        other_catalog = self.base / "edited-cases.json"
        other_catalog.write_text(json.dumps(edited), encoding="utf-8")
        self.assertFalse(self.suite.compare(before, before, self.catalog, other_catalog)["comparable"])

    def write(self, manifest, name):
        path = self.base / name
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_cli_exit_codes(self):
        path = self.write(self.manifest, "suite.json")
        command = [sys.executable, str(ROOT / "evals" / "suite.py")]
        accepted = subprocess.run([*command, str(path), "--cases", str(self.catalog)], capture_output=True, text=True)
        self.assertEqual((accepted.returncode, json.loads(accepted.stdout)["status"]), (0, "accepted"), accepted.stderr)
        del self.manifest["runs"][0]["review"]
        pending = subprocess.run([*command, str(self.write(self.manifest, "s2.json")), "--cases", str(self.catalog)],
                                 capture_output=True, text=True)
        self.assertEqual(pending.returncode, 1)
        (self.base / "broken.json").write_text("{broken", encoding="utf-8")
        broken = subprocess.run([*command, str(self.base / "broken.json"), "--cases", str(self.catalog)],
                                capture_output=True, text=True)
        self.assertEqual((broken.returncode, json.loads(broken.stdout)["status"]), (1, "invalid"))
        self.assertNotIn("Traceback", broken.stderr)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.suite = importlib.import_module("evals.suite")
        self.cases = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))

    def test_every_case_belongs_to_one_set_and_names_real_hosts(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertIn(case.get("set"), ("regression", "held-out"))
                self.assertTrue(set(case.get("hosts", ["claude"])) <= {"claude", "codex", "antigravity"})
        sets = {case["set"] for case in self.cases}
        self.assertEqual(sets, {"regression", "held-out"})

    def test_held_out_expectations_change_only_deliberately(self):
        self.assertEqual(self.suite.set_digest(self.cases, "held-out"), HELD_OUT_SHA256,
                         "held-out cases changed; see HELD_OUT_SHA256 before updating it")

    def test_discovery_cases_apply_to_their_own_host(self):
        for host in ("codex", "claude", "antigravity"):
            case = next(c for c in self.cases if c["id"] == f"discovery-{host}")
            self.assertEqual(case["hosts"], [host])
            self.assertIn("six_skills_discovered", [rule["field"] for rule in case["rules"]])


if __name__ == "__main__":
    unittest.main()
