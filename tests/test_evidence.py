"""Tests of an offline grader using synthetic evidence, not live agent runs."""
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


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.trace = b"Synthetic host fixture\nTests: 3 passed, 0 failed\nWorkers: 0\n"
        (self.base / "trace.txt").write_bytes(self.trace)
        self.case = {"id": "small-edit", "rules": [
            {"field": "workers", "op": "lte", "value": 1},
            {"field": "test_exit", "op": "eq", "value": 0},
            {"field": "tests_run", "op": "gte", "value": 1},
        ]}
        self.record = {
            "case_id": "small-edit", "origin": "synthetic",
            "source": {"path": "trace.txt", "sha256": hashlib.sha256(self.trace).hexdigest()},
            "observations": {
                "workers": {"value": 0, "lines": [3, 3]},
                "test_exit": {"value": 0, "lines": [2, 2]},
                "tests_run": {"value": 3, "lines": [2, 2]},
            },
        }

    def grade(self, record=None, case=None):
        self.assertTrue((ROOT / "evals/grade.py").is_file(), "Offline evidence grader has not been implemented")
        grader = importlib.import_module("evals.grade")
        return grader.grade(case or self.case, record or self.record, self.base)

    def test_success_is_explicitly_a_fixture(self):
        self.assertEqual(self.grade()["status"], "fixture-passed")

    def test_observed_is_not_implied_by_fixture(self):
        self.record["origin"] = "observed"
        self.assertEqual(self.grade()["status"], "passed")

    def test_failure_cannot_become_success(self):
        self.record["observations"]["test_exit"]["value"] = 1
        self.assertEqual(self.grade()["status"], "fixture-failed")

    def test_zero_tests_does_not_pass(self):
        self.record["observations"]["tests_run"]["value"] = 0
        self.assertEqual(self.grade()["status"], "fixture-failed")

    def test_missing_observation_is_not_verified(self):
        del self.record["observations"]["test_exit"]
        self.assertEqual(self.grade()["status"], "fixture-not-verified")

    def test_failure_wins_over_missing_observation(self):
        del self.record["observations"]["test_exit"]
        self.record["observations"]["tests_run"]["value"] = 0
        self.assertEqual(self.grade()["status"], "fixture-failed")

    def test_missing_source_is_not_verified(self):
        (self.base / "trace.txt").unlink()
        self.assertEqual(self.grade()["status"], "fixture-not-verified")

    def test_changed_source_is_invalid(self):
        (self.base / "trace.txt").write_text("different", encoding="utf-8")
        self.assertEqual(self.grade()["status"], "invalid")

    def test_empty_source_is_not_verified(self):
        (self.base / "trace.txt").write_bytes(b"")
        self.record["source"]["sha256"] = hashlib.sha256(b"").hexdigest()
        self.assertEqual(self.grade()["status"], "fixture-not-verified")

    def test_source_cannot_escape_record_directory(self):
        for path in ("../trace.txt", str(self.base / "trace.txt"), "C:/secret.txt", "a/../../trace.txt"):
            with self.subTest(path=path):
                record = copy.deepcopy(self.record)
                record["source"]["path"] = path
                self.assertEqual(self.grade(record)["status"], "invalid")

    def test_symlink_cannot_escape_record_directory(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "outside.txt"
            target.write_bytes(self.trace)
            link = self.base / "linked.txt"
            try:
                link.symlink_to(target)
            except OSError as error:
                self.skipTest(f"OS does not allow test symlink: {error}")
            self.record["source"]["path"] = "linked.txt"
            self.assertEqual(self.grade()["status"], "invalid")

    def test_bool_is_not_a_numeric_worker_count(self):
        self.record["observations"]["workers"]["value"] = False
        self.assertEqual(self.grade()["status"], "invalid")

    def test_missing_or_out_of_range_provenance_is_not_verified(self):
        for lines in (None, [], [0, 1], [2, 1], [1, 100], [True, 2]):
            with self.subTest(lines=lines):
                record = copy.deepcopy(self.record)
                record["observations"]["workers"]["lines"] = lines
                self.assertEqual(self.grade(record)["status"], "fixture-not-verified")

    def test_wrong_case_and_unknown_origin_are_invalid(self):
        for key, value in (("case_id", "other"), ("origin", "guessed")):
            record = copy.deepcopy(self.record)
            record[key] = value
            self.assertEqual(self.grade(record)["status"], "invalid")

    def test_unsupported_operator_is_invalid(self):
        self.case["rules"][0]["op"] = "execute"
        self.assertEqual(self.grade()["status"], "invalid")

    def test_empty_rules_never_pass(self):
        self.case["rules"] = []
        self.assertEqual(self.grade()["status"], "invalid")

    def test_unknown_observation_and_duplicate_rules_are_invalid(self):
        self.record["observations"]["typo"] = {"value": 0, "lines": [1, 1]}
        self.assertEqual(self.grade()["status"], "invalid")
        del self.record["observations"]["typo"]
        self.case["rules"].append(self.case["rules"][0])
        self.assertEqual(self.grade()["status"], "invalid")

    def test_false_review_fingerprint_fails(self):
        case = {"id": "small-edit", "rules": [{"field": "review_matches_final", "op": "eq", "value": True}]}
        self.record["observations"] = {"review_matches_final": {"value": False, "lines": [1, 1]}}
        self.assertEqual(self.grade(case=case)["status"], "fixture-failed")

    def test_grader_does_not_mutate_inputs(self):
        before = copy.deepcopy((self.record, self.case))
        self.grade()
        self.assertEqual((self.record, self.case), before)

    def test_every_catalog_rule_rejects_a_counterexample(self):
        """Synthetic contract checks; these are not executions of the tasks."""
        activity_fields = importlib.import_module('evals.grade').ACTIVITY_FIELDS
        cases = json.loads((ROOT / "evals/cases.json").read_text())
        for case in cases:
            record = copy.deepcopy(self.record)
            record["case_id"] = case["id"]
            record["observations"] = {
                rule["field"]: {"value": rule["value"], "lines": [1, 1]}
                for rule in case["rules"] if rule['field'] not in activity_fields
            }
            count = max([r['value'] for r in case['rules']
                         if r['field'] in ('workers_total', 'returned_workers') and r['op'] == 'gte'] or [0])
            record['activity'] = {'complete': True, 'lines': [1, 3], 'events': [
                {'event': event, 'actor': str(i), 'lines': [1, 1]}
                for i in range(count) for event in ('start_helper', 'result', 'stop_helper')]}
            with self.subTest(case=case["id"], mode="synthetic-valid"):
                self.assertEqual(self.grade(record, case)["status"], "fixture-passed")
            for rule in case["rules"]:
                if rule['field'] in activity_fields:
                    continue  # Lifecycle-derived metrics have dedicated behavior tests.
                bad = copy.deepcopy(record)
                value = rule["value"]
                replacement = (not value) if type(value) is bool else value - 1 if rule["op"] == "gte" else value + 1
                bad["observations"][rule["field"]]["value"] = replacement
                with self.subTest(case=case["id"], field=rule["field"]):
                    self.assertEqual(self.grade(bad, case)["status"], "fixture-failed")

    def test_cli_pass_failure_and_missing_evidence_exit_codes(self):
        record_path = self.base / "record.json"
        cases_path = self.base / "cases.json"
        cases_path.write_text(json.dumps([self.case]), encoding="utf-8")
        for mode in ("pass", "fail", "missing"):
            record = copy.deepcopy(self.record)
            if mode == "fail":
                record["observations"]["test_exit"]["value"] = 1
            if mode == "missing":
                del record["observations"]["tests_run"]
            record_path.write_text(json.dumps(record), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "evals/grade.py"), str(record_path), "--cases", str(cases_path)],
                capture_output=True, text=True,
            )
            with self.subTest(mode=mode):
                self.assertEqual(result.returncode, 0 if mode == "pass" else 1)
                self.assertIn(json.loads(result.stdout)["status"],
                              ("fixture-passed", "fixture-failed", "fixture-not-verified"))

    def test_malformed_cli_input_returns_nonzero_without_traceback(self):
        self.assertTrue((ROOT / "evals/grade.py").is_file(), "Offline evidence grader has not been implemented")
        path = self.base / "bad.json"
        path.write_text("{broken", encoding="utf-8")
        result = subprocess.run([sys.executable, str(ROOT / "evals/grade.py"), str(path)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)

    def test_duplicate_json_fact_cannot_overwrite_a_failure(self):
        cases_path = self.base / "cases.json"
        cases_path.write_text(json.dumps([self.case]), encoding="utf-8")
        path = self.base / "duplicate.json"
        record_text = json.dumps(self.record).replace('"test_exit": {"value": 0',
                                                     '"test_exit": {"value": 1, "value": 0')
        path.write_text(record_text, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ROOT / "evals/grade.py"), str(path), "--cases", str(cases_path)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
