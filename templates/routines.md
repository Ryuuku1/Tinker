# Opt-in maintenance routines

Two prompt templates for a host's own scheduler. Nothing here creates a schedule: create
one only when the user asks, through the
[team workflow](../.agents/skills/tinker-team/SKILL.md), which validates the plan
with `schedule-plan`. Each run is unattended, so consequential operations are denied;
it proposes and reports, and the user decides in a later, attended chat.

## Weekly learning review

- Schedule: `0 9 * * 1` (Mondays at 09:00), or the user's choice.
- Plan: `schedule-plan --app <claude|codex|antigravity> --role researcher --repo <repository> --cron "0 9 * * 1" --task "<task>"`
- Task: Review this week's knowledge candidates for <repository> under the Tinker
  checkout's .tinker folder. Revalidate each against current source. Propose at most
  three improvements, each naming its evidence, its destination and the behavioral case
  that would show it works. Apply, commit, publish and install nothing.

## Periodic compatibility review

- Schedule: `30 9 * * 5` (Fridays at 09:30), or the user's choice.
- Plan: `schedule-plan --app <claude|codex|antigravity> --role researcher --repo <Tinker checkout> --cron "30 9 * * 5" --task "<task>"`
- Task: Recheck the Codex, Claude Code and Antigravity hook and tool documentation cited
  in docs/providers.md against TOOL_KINDS in scripts/tinker_runtime.py and the matchers in
  scripts/install_apps.py. Report each discrepancy with its source URL and date. Change
  no files.

## Creating one in each host

- Claude Code: `create_scheduled_task` with `taskId` = the plan's `task_id`, its `prompt`
  and `description`, and `cronExpression` = its `cron`. Pass `notifyOnCompletion` only as
  the user chose; when updating a task, omit it so an existing notification choice is kept.
- Codex: `automation_update` with kind `cron`, the plan's `description` as its name, its
  `prompt` and `rrule`, and the repository as its target. Keep the user's notification
  settings in the app.
- Antigravity: manual. Give the user the plan's `cron` and `prompt` for Scheduled Tasks;
  its scheduled runs are unverified.
