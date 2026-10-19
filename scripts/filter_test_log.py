"""Keep the actionable part of a noisy test or build log: failure blocks, errors, stack traces and totals.

    python scripts/filter_test_log.py <log file>        or        <command> | python scripts/filter_test_log.py

Passing tests, skipped-test lines and compiler warnings are dropped; failure blocks are kept up to --max-lines; summary
lines (totals, failure counts) are always kept, even past the cap, and the output ends with what was trimmed, as the
evidence policy requires. Standard library only; deterministic, so the same log always gives the same summary.
"""
import argparse
import re
import sys

NOISE = re.compile(r"(?i)(:\s*warning(\s+[A-Za-z0-9]+)?:\s*|^\s*warning(\s+[A-Za-z0-9]+)?:\s*|\bwarning\s+(CS|TS)\d+:"
                   r"|^\s*(Passed|PASS)\s+|[✓√]\s+|\bPASSED\b|^\s*Skipped\s+|\bSKIPPED\b"
                   r"|^\s*(Time Elapsed|Build started|Total time:))")
FAILURE = re.compile(r"(?i)(Failed\s+[\w.]+|^\s*FAIL\s+|●|AssertionError|Expected:|Received:|Stack\s*Trace:"
                     r"|^\s*at\s+[\w.<>$]+\(.*\)|:\s*error(\s+[A-Za-z0-9_-]+)?:\s*|:\s*error\[[A-Za-z0-9]+\]:"
                     r"|^\s*error(\s+[A-Za-z0-9_-]+)?:\s*|^\s*error\[[A-Za-z0-9]+\]:|ERROR:|\bFAILED\b"
                     r"|^(FAIL|ERROR): |^Traceback \(most recent call last\):|^=+ (FAILURES|ERRORS) =+$)")
COUNTED = re.compile(r"(?i)(Failed\s+[\w.]+|^\s*FAIL\s+|●|:\s*error|^\s*error|^ERROR:|^FAIL:)")
SUMMARY = re.compile(r"(?i)(Total tests:|^\s*Failed:\s*\d+|^\s*Passed!|^\s*Failed!|Tests:.*\b(failed|passed)\b"
                     r"|FAILED\s+\(|^Ran \d+ tests? in|^OK(\s+\(|$)|^=+ .*\b(passed|failed|error)s?\b.* =+$"
                     r"|\b\d+ (passed|failed)\b|Build (succeeded|FAILED)|\d+ Error\(s\)|\d+ Warning\(s\))")


def summarize(lines, max_lines=50):
    kept, summaries = [], []
    capturing, blanks, failures, dropped = False, 0, 0, 0
    for line in lines:
        if SUMMARY.search(line):
            summaries.append(line)
            capturing = False
            continue
        if NOISE.search(line):
            dropped += 1
            continue
        if FAILURE.search(line):
            capturing, blanks = True, 0
            failures += bool(COUNTED.search(line))
        elif capturing and not line.strip():
            blanks += 1
            if blanks > 2:
                capturing = False
                dropped += 1
                continue
        elif capturing:
            blanks = 0
        else:
            dropped += 1
            continue
        if len(kept) < max_lines:
            kept.append(line)
        else:
            dropped += 1
    if not kept and not summaries:
        clean = [line for line in lines if line.strip() and not NOISE.search(line)]
        if not clean:
            return "No test or compiler failures detected (no output besides passes, skips and warnings)."
        tail = clean[-20:]
        return "\n".join(["--- no failure markers found; last lines ---", *tail,
                          f"[filter: showed the last {len(tail)} of {len(lines)} lines]"])
    out = kept + (["--- summary ---", *summaries] if summaries else [])
    out.append(f"[filter: {failures} failure marker(s); kept {len(kept)} block line(s) and {len(summaries)} summary "
               f"line(s); dropped {dropped} of {len(lines)} lines (passes, skips, warnings, context"
               f"{', and block lines past the cap of ' + str(max_lines) if len(kept) >= max_lines else ''})]")
    return "\n".join(out)


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
