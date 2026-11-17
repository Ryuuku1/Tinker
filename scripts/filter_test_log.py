"""Keep the actionable part of a noisy test or build log: failure blocks, errors, stack traces and totals.

    python scripts/filter_test_log.py <log file>        or        <command> | python scripts/filter_test_log.py

Passing tests, skipped-test lines and compiler warnings are dropped; failure blocks are kept up to --max-lines; summary
lines (totals, failure counts) are always kept, even past the cap, and the output ends with what was trimmed, as the
evidence policy requires. Standard library only; deterministic, so the same log always gives the same summary.
In Claude, the runtime's post-tool hook applies the same filter to long test, build and lint output.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
# One copy of the filter: the runtime's PostToolUse trim (Claude) uses it too, and the installed runtime runs
# alone, so the filter lives there and this file is its command line.
from tinker_runtime import COUNTED, FAILURE, NOISE, SUMMARY, summarize  # noqa: E402,F401


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("log", nargs="?", help="log file; reads standard input when omitted")
    parser.add_argument("--max-lines", type=int, default=50, help="cap on failure-block lines (summaries always kept)")
    args = parser.parse_args(argv)
    if args.log:
        with open(args.log, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    if not text.strip():
        print("No test output to filter.")
        return 0
    print(summarize(text.splitlines(), max(1, args.max_lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
