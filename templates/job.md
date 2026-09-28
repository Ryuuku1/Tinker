---
task_id: <UUID, equal to this file's name>
status: active
repository: <absolute primary checkout path>
worktree: <absolute worktree path, or the repository path when there is none>
host_session: <chat reference from the Tinker context, or the host's own session reference>
---

# Job <UUID>: <short objective>

Copy into the package's ignored `.tinker/tasks/<UUID>.md` for substantial or
delegated work. Fill with actual observations; remove unused sections. The Lead
alone updates this file while holding writing ownership. Never save secrets.
Keep `status` to active, paused, blocked or completed: installed hooks and
`status` read only these front matter fields, never the body.

## Ownership and scope

- Ownership: active / released / uncertain
- Current writer: Lead / actual helper ID / none
- Objective and acceptance criteria:
- Authorized actions; actions still requiring authorization:
- Package root; command working directory:
- Buzz scope, when run through Buzz (relay, channel, thread); its own worktree:
- Starting revision; staged/unstaged changes; untracked user files:

## Work and evidence

- Decisions and relevant role charters:
- Helpers: native ID, role, assignment, actual start/end state, result reference.
  Missing or failed results stay marked missing; assignment is not contribution.
- Owned file changes and artifact paths:
- Checks: exact command, directory, exit status, test counts, source evidence and
  revision/content fingerprint. Record failed/skipped/unavailable checks explicitly.
- Review: actual reviewer ID, inspected content fingerprint, findings/resolution.
- Relevant verified knowledge references; unresolved assumptions:

## Handoff

- Remaining work and blockers:
- Old host and helpers confirmed stopped/paused:
- Last verified repository state and relevant file fingerprints:
- On resume: compare actual state, invalidate stale tests/reviews/approvals, then
  record the new owner. Never infer ownership from the newest file or its timestamp.
