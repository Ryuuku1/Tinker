# Worker brief

Copy into `<Tinker root>/.tinker/evidence/<UUID>/codex-<n>-<mode>-brief.md` for one
`codex exec` run ([external workers](../policies/external-workers.md)), fill every
field with actual values, remove these two paragraphs and feed the file on stdin.
Inline everything the worker needs: it cannot be assumed to resolve the Tinker root.

For feedback, write a new brief that inlines the previous answer and the Lead's
corrections under Objective; never resume a run.

---

You are a worker: print no Triage line, write no retro or checkpoint, spawn no
helpers, never run codex. The Lead owns triage, review and the final answer.

## Objective

<one bounded outcome>

## Acceptance condition

<observable result that proves it, for example a test that passes>

## Mode and sandbox

<study | plan | implement>, sandbox `<read-only | workspace-write>`.

## Locations

- Tinker root: <absolute path>
- Target checkout or worktree (your working root): <absolute path>
- Base revision: <commit>; baseline state: <clean, or the files already changed>

## Files you may change

<implement: the exact paths; everything else is read-only. study and plan: none>

## Gate

<command, working directory, and what green means (for example "12 passed, 0 failed")>.
If the sandbox denies the gate, report the denial verbatim in your handoff; that is
not a failure, and the Lead reruns the gate.

## Charter

<implement: the body of roles/engineer.md; study and plan: the body of
roles/researcher.md, without its web sources>

## Rules

- Never commit, stage or push.
- No network: no web, no package downloads; use local sources only.
- Change only the files listed above; no other edits, generated files or
  formatting churn.
- Stop and report instead of working around a denial.

## Output

End with a compact handoff:

- Outcome: done, partial or blocked, in one line.
- Files and lines: each path with its changed or cited lines.
- Commands actually run, each with its result.
- Unresolved risks and open questions.

Study adds, before the handoff: question; answer; evidence (`path:line`); verified
facts, inferences and unknowns kept apart; options and tradeoffs.

Plan adds, before the handoff: goal; files to change, each with why; ordered steps;
the gate command and expected result; risks.
