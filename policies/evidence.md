# Evidence

Choose evidence proportional to the claim. Record command, working directory,
revision or relevant file/diff fingerprint, exit status and concise result when
running checks. Keep the raw result in the native session or a local task record
when continuation needs it; redact secrets before copying output.

- Code: inspect actual changed files and run checks appropriate to changed behavior.
- Defect: observed symptom, root-cause evidence and regression proof; label unproven
  hypotheses. Show a failing reproduction before a fix when feasible.
- Review: scope, comparison base, inspected final content, finding location,
  consequence and evidence. No findings means no findings in that scope, not proof
  of correctness. An edit to reviewed content invalidates that part of the review.
- Research: repository references or current primary sources, with uncertainty
  separated from fact. Do not fabricate browsing, citations or graph queries.
- Product/design: concrete acceptance examples and usable flows or artifacts;
  distinguish observed behavior from recommendations and untested mockups.
- Documentation/delivery: inspectable artifacts and source-backed instructions;
  clearly separate prepared, executed and published outcomes.
- Team contribution: actual native helper identity, returned evidence and its
  inspected scope. An assignment, timeout or Lead role switch is not a review.

An exit code of zero is insufficient when no tests were discovered. Build success
does not imply tests ran. Skipped, crashed, timed-out and unavailable checks stay
visible; inspect both process status and test-runner summary. Never filter away
failure or skipped-test totals. After changing tested behavior, rerun affected
checks. A pre-existing failure is still a failure, with attribution if established.
Trimming noisy output such as banners, progress lines and out-of-scope warnings
must keep actionable errors, failure blocks, stack traces and totals, and state
what was trimmed. Review reading may skip lockfile content only where
[tool guidance](tools.md) allows; never omit a lockfile from the change inventory.

Use `succeeded`, `failed`, `partial`, `skipped`, `blocked` or `not-verified` when a
status helps. `succeeded` applies only to demonstrated scope. A task can be partial
while its completed checks passed. Missing evidence is `not-verified`.
Do not infer elapsed time, token usage or reductions from character counts.
Provider-reported usage may be quoted with its measurement scope.

The final answer owns all material failures and limitations. Native traces,
observed artifacts and explicit unknowns provide observability without a status
engine or private reasoning transcript.
