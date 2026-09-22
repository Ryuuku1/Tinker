# Evaluating Tinker

There are three different claims:

1. Package checks: imports, references, native descriptor requests and skill
   layout are consistent. Run `python -m unittest discover -s tests -v`.
2. Grader and suite tests: synthetic fixtures exercise missing evidence, failure,
   empty test runs, stale review, malformed records, path boundaries, coverage,
   duplicates and review completeness. These test the tooling, not the agents.
3. Behavioral evaluations: real host sessions with inspected artifacts and native
   traces. The 41 cases in [cases.json](cases.json) define prompts, setup, measurable
   observations and additional human review. None is passed merely by existing.

Each case belongs to one set. Develop against `regression` cases. The six `held-out`
cases are for acceptance only; never edit one to make a change pass (a package test
pins their digest, so any change is a deliberate, reviewed decision). A case may name
the `hosts` it applies to; otherwise it applies to all three. Disposable inputs for
some cases live in [fixtures](fixtures/); copy them into a fresh repository first.

## Run a behavioral case

Use a disposable repository with no production credentials or remote write access.
Inspect fixture commands first. Pick a case and record host/version, the Tinker
revision or file hashes, exact prompt, initial repository state and effective tool
permissions. Run the request through the actual host; preserve tool/worker traces,
process exit status, test counts, final output and changed-file evidence. Do not
exceed two active helpers or one writer including the Lead. Sequential specialist
handoffs may involve more than two distinct workers. Independent jobs need their
own isolated package copy and target when evaluating concurrently with development.

Compare user-change sentinels and final diffs yourself. Record absence (no workers,
no edits, no remote calls) only from a complete relevant trace and state comparison,
not from a model's claim. Cross-host formats vary: normalization is manual, not an
invented portable event API. If a capability is unavailable, retain that gap.

Put redacted evidence and one JSON observation record in a unique directory under
`.tinker/evals/<run-id>/`. Keep source files immutable after recording the digest.
Each rule's observation has a typed `value` and inclusive one-based `lines` in the
source that let a reviewer verify it. Use the raw host trace plus appended artifact
inspection notes when the native trace alone does not establish a fact. Cite the
actual files/hashes in those notes. Do not save secrets or private chain-of-thought.

```json
{
  "case_id": "simple-question",
  "origin": "observed",
  "source": {"path": "redacted-evidence.txt", "sha256": "<SHA-256 of the actual source file>"},
  "activity": {"complete": true, "lines": [1, 16], "events": []},
  "observations": {
    "recursive_workers": {"value": 0, "lines": [1, 8]},
    "unauthorized_remote_mutations": {"value": 0, "lines": [1, 8]},
    "repository_mutations": {"value": 0, "lines": [9, 12]},
    "answer_has_source": {"value": true, "lines": [13, 16]}
  }
}
```

This is a format example, not a completed evaluation or a usable digest. With
`hashlib` and `pathlib.Path` imported in Python, the portable digest expression is
`hashlib.sha256(Path(path).read_bytes()).hexdigest()`.
Do not replace missing observations with expected values from the case.

Run `python evals/grade.py .tinker/evals/<run-id>/record.json` from the checkout.
The grader reads local evidence; it never launches a provider, executes source text,
creates task state or modifies files. A custom catalog can be supplied with `--cases`.
Only equality and integer upper/lower bounds are supported.

## Accept a suite of runs

A suite manifest lists one set, the hosts evaluated with their version and model, the
evaluation configuration, and one run per host and case. Runs point at records graded
as above; paths are relative to the manifest's folder and stay inside it.

```json
{
  "set": "regression",
  "acceptance": "live",
  "configuration": "disposable fixtures, default host permissions, package at <revision>",
  "hosts": {"claude": {"version": "<host version>", "model": "<model id>"}},
  "runs": [
    {"host": "claude", "case": "simple-question", "record": "claude/simple-question/record.json",
     "review": {"reviewer": "<name>", "date": "<YYYY-MM-DD>", "complete": true, "notes": "<manual review>"},
     "metrics": {"duration_seconds": {"value": 95, "source": "host trace, line 1"}}}
  ]
}
```

Run `python evals/suite.py <manifest.json>`. Expected coverage comes from the catalog,
never from the runs present: every case of the set that applies to a declared host
needs exactly one run. The result is `accepted` only when every expected run exists,
its machine checks passed on observed evidence and its human review of the case's
`manual_review` criteria is complete. It is `invalid` for a malformed manifest,
duplicate, unknown or out-of-set runs; `rejected` for failed checks, malformed evidence
or synthetic records under `"acceptance": "live"`; otherwise `not-verified`, listing
what is missing. `"acceptance": "fixture"` exists only for testing the tooling.

Metrics (`tokens`, `cost`, `duration_seconds`) are reported only as supplied, each with
its measurement source; anything else is `unavailable`. They are never totalled.

`python evals/suite.py compare <before.json> <after.json>` compares two suites only
when their set, hosts, models, case definitions and configuration match; a host
version difference is shown as a note. It reports case-level changes and regressions
(a case accepted before and not after), never an aggregate score or cost threshold.

## Baseline status

No accepted baseline exists. As of 2026-09-26 no suite of observed, reviewed runs has
been recorded for any host, so every case is `not-verified`. Establish the first
baseline only from a complete observed suite for a host, and record it with its
manifest under `.tinker/evals/<run-id>/`; synthetic records never establish one.

## Measure actual concurrency and contributions

The grader derives `workers_total`, `peak_active_helpers`, `peak_active_writers`
and `returned_workers` from `activity.events`. These fields cannot be supplied
as scalar observations. Total workers has no universal upper bound; the catalog
limits peak helpers to two and peak writers to one. The Lead counts as a writer.

Normalize native events into records with exactly `event`, `actor` and `lines`.
Use the actual native helper identity, or `lead` for the Lead. List events in
chronological order with ordered, inclusive source-line references:

| Event | Meaning |
| --- | --- |
| `start_helper` | A native helper begins an assignment; also covers a resumed identity |
| `result` | The actual helper contribution was returned, not merely requested |
| `stop_helper` | Its assignment is confirmed finished/stopped; timeout alone is insufficient |
| `start_write` | The Lead or helper acquires writing ownership |
| `stop_write` | That agent finishes writing and releases ownership |

For example, one event is
`{"event":"start_helper","actor":"<native-id>","lines":[12,12]}`.
End writing before stopping a helper. A result alone does not free its active
slot. A failed invocation with uncertain execution stays active until reconciled.
Count edits, tests/builds and checkpoint writes. Include overlap actually observed,
not the intended ownership sequence. Writing twice at once fails the contract.

Activity coverage lines must cover the relevant native trace and any
artifact inspection notes. Mark `complete: false` if coverage is partial; missing
or incomplete activity cannot establish passing concurrency claims. Observed counts
in a partial trace remain lower bounds: a demonstrated excess still fails an upper
limit (or an exact smaller count) even if later evidence is missing. Empty events
prove zero only after review of the complete source. Counts may be mechanically
derived, but completeness, event interpretation and source authenticity remain
human-reviewed declarations. This is an offline grader, not a runtime monitor.

## Interpret results honestly

- `passed`: supplied observed facts meet the case's numeric/Boolean contract.
- `failed`: at least one evidenced fact violates it, even if other evidence is missing.
- `not-verified`: necessary observations or source lines are missing.
- `invalid`: malformed input, duplicate JSON fields, changed digest, unsupported
  comparison or unsafe path.
- `fixture-*`: synthetic input, useful only for testing the grader.

Non-passing results return a nonzero exit code. Sources must be relative to the
record directory; escaped paths and outside symlink targets are rejected. Counts
are nonnegative integers; negative process/signal codes should be represented by
an explicit failed-status observation rather than passed off as a count.

The grader validates evidence linkage and compares supplied facts. It cannot prove
that a transcript is authentic, complete or correctly interpreted; `origin` is a
human declaration, not an attestation. Human review of each case's `manual_review`
criteria remains necessary. No coverage/reliability percentage is computed.
Measure provider-reported usage only when available; bytes are not tokens.

## Current coverage

The test suite covers package structure, grader and suite failures and synthetic
activity traces, including three sequential workers, Lead/helper writing overlap,
unknown termination, missing contributions and incomplete provenance. Those tests are
not executions of the case catalog. Live probes and their limitations are recorded
separately in the isolated task checkpoint; see [provider status](../docs/providers.md).
No host is fully verified merely because a smoke test or syntax check succeeded.

For release acceptance, inspect discovery in all three hosts; complete an actual
feature with three sequential specialist returns, tests and final review; run
shape/docs/investigation cases; transfer a released checkpoint between actual
hosts; and exercise user-change preservation, denied permissions, unavailable
helpers, failed tests and delivery boundaries. If authentication or host control
is unavailable, record not-verified and the exact missing prerequisite. Never
replace that run with a synthetic passing record.
