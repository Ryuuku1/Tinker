import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import filter_test_log  # noqa: E402

UNITTEST_LOG = """test_a (tests.test_x.T.test_a) ... ok
test_b (tests.test_x.T.test_b) ... FAIL
======================================================================
FAIL: test_b (tests.test_x.T.test_b)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "tests/test_x.py", line 9, in test_b
    self.assertEqual(1, 2)
AssertionError: 1 != 2

----------------------------------------------------------------------
Ran 2 tests in 0.001s

FAILED (failures=1)
"""

DOTNET_LOG = "\n".join(
    ["Build started 10/19/2026", "src/A.cs(3,1): warning CS0168: unused variable"]
    + [f"  Passed Ns.Tests.Case{i} [1 ms]" for i in range(500)]
    + ["  Failed Ns.Tests.Broken [3 ms]", "  Error Message:", "   Expected: 2", "   Actual: 1",
       "  Stack Trace:", "     at Ns.Tests.Broken() in T.cs:line 12", "",
       "Failed!  - Failed:     1, Passed:   500, Skipped:     0, Total:   501"])


class FilterTestLogTests(unittest.TestCase):
    def test_unittest_failure_block_and_totals_survive(self):
        out = filter_test_log.summarize(UNITTEST_LOG.splitlines())
        self.assertIn("FAIL: test_b", out)
        self.assertIn("AssertionError: 1 != 2", out)
        self.assertIn("Ran 2 tests", out)
        self.assertIn("FAILED (failures=1)", out)
        self.assertNotIn("... ok", out)

    def test_passes_and_warnings_are_dropped_and_the_trim_is_stated(self):
        out = filter_test_log.summarize(DOTNET_LOG.splitlines())
        self.assertNotIn("Case42", out)
        self.assertNotIn("warning CS0168", out)
        self.assertIn("Failed Ns.Tests.Broken", out)
        self.assertIn("at Ns.Tests.Broken()", out)
        self.assertIn("Total:   501", out)
        self.assertRegex(out, r"\[filter: \d+ failure marker\(s\); .*dropped \d+ of \d+ lines")

    def test_summary_lines_are_kept_past_the_cap(self):
        lines = [f"FAIL: test_{i}" for i in range(80)] + ["Ran 80 tests in 1s", "FAILED (failures=80)"]
        out = filter_test_log.summarize(lines, max_lines=10)
        self.assertIn("FAIL: test_9", out)
        self.assertNotIn("FAIL: test_10\n", out)
        self.assertIn("FAILED (failures=80)", out)
        self.assertIn("past the cap of 10", out)

    def test_no_markers_falls_back_to_the_tail(self):
        out = filter_test_log.summarize(["something odd happened", "exit code 3"])
        self.assertIn("no failure markers found", out)
        self.assertIn("exit code 3", out)

    def test_cli_reads_stdin(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/filter_test_log.py")], input=UNITTEST_LOG,
                                capture_output=True, text=True, check=True)
        self.assertIn("FAILED (failures=1)", result.stdout)


if __name__ == "__main__":
    unittest.main()
