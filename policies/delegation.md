# Delegation

The concurrency budget is defined in [AGENTS.md](../AGENTS.md). Track actual native
worker identities, assignments, running/stopped state and returned evidence.
At most two helpers may be active; several may contribute sequentially. Reuse a
worker when its context remains useful. Do not spawn a replacement for a timed-out
or uncertain worker until its termination is confirmed. An idle but unfinished
assignment still occupies capacity; completed workers can be resumed within it.
No automatic explainer, tester or reviewer after ordinary work.

Exactly one agent may hold writing ownership at a time, including the Lead.
The Lead records the grant in the job checkpoint before dispatch and refrains
from all file changes while a helper holds it. Helpers return evidence; they do
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
