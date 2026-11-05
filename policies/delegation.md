# Delegation

The delegation rules are summarized in [AGENTS.md](../AGENTS.md). Track actual native
worker identities, assignments, running/stopped state and returned evidence.

## Team size

Pick the number of helpers per task for the best result per cost; there is no
fixed ceiling. Before dispatch, say in one line how many and why.

- Count the independent, bounded pieces: separate areas to search or analyze,
  changes on disjoint files, a review or test pass that needs fresh context.
  Steps where one needs another's result, or that touch the same files, are one piece.
- A piece gets its own helper only when running it in parallel or in a clean
  context saves more than the helper costs: the handoff, the context it rereads
  and the Lead's time checking and integrating its result. A few tool calls, a
  lookup with a known target, or a step whose result the Lead needs next stays
  with the Lead. Most tasks need 0 helpers; broad independent work gets one per piece.
- Use the cheapest capable helper: the Explorer for search, a read-only role for
  analysis or review, a writer only for edits.
- Recount when the work changes: release a helper whose piece is done, add one
  when a new independent piece appears. Several specialists may contribute in
  sequence. The host's concurrency limit and any limit the user states apply.

## Running helpers

Reuse a worker when its context remains useful. Do not spawn a replacement for a timed-out
or uncertain worker until its termination is confirmed. An idle but unfinished
assignment still occupies capacity; completed workers can be resumed within it.
No automatic explainer, tester or reviewer after ordinary work.

Exactly one agent may hold writing ownership of a working tree at a time,
including the Lead. Parallel writers each get their own worktree from the same
base, with disjoint files named in the assignment; the Lead applies their results
one at a time and reruns the gate on the combined change. The Lead records each
grant in the job checkpoint before dispatch and refrains from file changes in a
working tree while a helper holds it. Helpers return evidence; they do
not update the shared checkpoint. Stop writing, obtain the actual result and
confirm the helper's turn ended before transferring ownership. Commands that may
write (including tests/builds) require ownership. Worktrees preserve changes but
do not relax this policy. This is a coordination agreement, not a filesystem lock.

Before spawning, identify a bounded deliverable that can run independently or
provide meaningful independent verification. Resolve the effective tool set and
permissions, not just the requested descriptor, and check they cover the assignment
before dispatch: a reader without file tools gets bounded source excerpts, a researcher
without web tools gets sources the Lead collected, or the Lead does the work. Never
widen permissions merely to complete an assignment. Children get local read/search
by default. Grant local edits and command execution only to an assigned writing
role where needed; repository test scripts can write. No external MCP/plugin tools by default.
Researcher source access must be explicitly scoped to the assignment.

Reviewer gets read/search only: no editing, shell, tests, remote mutations or
delegation. Do not grant a shell merely to run Git; the Lead supplies a diff and
its baseline identity. Native read-only filesystem access does not block remote
tools. If the host cannot establish required restrictions, keep the work in the
Lead and report the lack of independent review. See [providers](../docs/providers.md).

Send only: objective; acceptance condition; Tinker root; target repo/worktree;
relevant source/diff references and current revision; baseline user changes;
allowed tools/paths; writing owner; role charter; no-recursion rule; expected output.
If the host cannot read the charter with the assigned tools, the Lead includes
its canonical contents in the handoff rather than widening helper permissions.
Avoid inherited full conversation context when a concise handoff suffices.

Return a compact handoff: outcome; findings; file/line or source evidence; commands
actually executed; unresolved risks. The Lead checks claims against artifacts and
the final diff. A timeout, skipped reviewer or failed invocation is not a review.
Stop repeated identical tool failures and change approach; do not silently retry
through a more privileged provider. Native session follow-ups are sufficient.

Read-only specialist profiles return briefs, designs and research to the Lead.
If an authorized artifact needs writing, the Lead saves it after reacquiring
ownership, or assigns it to a configured writing role. A role name never grants
new tools. Browser/source access unavailable to a specialist can be collected by
the Lead within scope and included as evidence.
