# Workspace and continuation

Resolve explicit repository paths and read each target's own guidance. Inspect
the package root (instructions and checkpoints), target root (product files) and
command working directory separately. Set commands' working directory explicitly;
never create a product inside the package merely because it is the launch folder.
Directory access does not imply target instruction discovery. Missing access
requires the host's native directory/workspace controls, never a permission bypass.
Inspect Git root, branch/HEAD, staged diff, unstaged diff and untracked files before editing.
For a new repository with no HEAD or a non-Git folder, record that fact and use a
file inventory; do not interpret a failed Git command as a clean workspace.
An ambiguous target blocks mutations, not independent research.

Existing edits belong to the user unless this task demonstrably created them.
Never reset, stash, revert or overwrite unrelated changes. When an edited area
overlaps the task, inspect it and preserve intent; ask only for a real conflict.
Preserve existing encoding and line endings, including mixed endings. Inspect the
diff for whole-file normalization after a small edit; reapply only the owned edit
when the editing tool causes unrelated churn. Follow repository formatting rules.
Do not change a repository-wide architecture document for ticket notes. Change
that document only when the user task actually includes architecture work.

Use native worktree facilities for risky isolated changes or separate jobs.
Verify the starting commit: worktrees do not automatically include uncommitted
changes and provider defaults can start from a different branch. Supply a scoped
patch or explicit starting state only when required and preserve the original.
For a new worktree, verify the intended base from current repository evidence;
never assume `main` or `master`, or treat a surviving old remote ref as the default.
Do not copy credentials into a worktree. Within a job a second writer must wait,
even in another worktree; no custom lock service. Recheck drift before applying results.
Retain dirty or active worktrees; never force-remove them on task completion.

For explicitly requested multi-repository changes, identify every target and its
allowed mutation scope. Work and verify per repository; record dependency order
and report partial completion if one fails. No cross-repository atomicity promise.

Prefer native session resume within a host. For substantial or delegated work, or
when the user requests a handoff, create
`.tinker/tasks/<UUID>.md` under the Tinker checkout, with an optional ticket
label in its contents. Use the [checkpoint template](../templates/job.md).
Create the UUID once, reuse it for that task, and never
select a task merely because it is newest. Record objective, exact repo/worktree
paths, revisions, original dirty changes, owned changes, real checks/results,
acceptance criteria, actual worker contributions, current host/session and writer,
authorization scope and remaining work. Update at meaningful handoffs and before
stopping, when the Lead holds writing ownership. No secrets or private
reasoning. Do not create task reports in target product repositories. Installed
hooks and `status` read only the front matter (task id, status, repository,
worktree, host session) and never edit a checkpoint; presence is not a release.

Before resuming, compare actual paths, revisions and relevant file state; stale
checks/approvals scoped to a different action are not transferable. Clarify
ambiguous task identity. A cross-host handoff transfers facts, not provider session
IDs or a promise of conversation migration. Stop or pause the old session and its
helpers, mark the checkpoint released, then let the new host claim it after state
revalidation. If ownership is active or uncertain, do not start another writer;
ask the user to stop the previous session. Checkpoints are not automatic locks.
Multiple jobs use separate handoffs. Ordinary questions require no checkpoint.
No auto-cleanup:
delete only an explicitly selected owned artifact after checking it is inactive,
inside the authorized root and no longer needed. Never follow links during deletion.
