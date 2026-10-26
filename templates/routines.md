# Opt-in maintenance routines

Prompt templates for a host's own scheduler. Nothing here creates a schedule: create
one only when the user asks, through the
[team workflow](../.agents/skills/tinker-team/SKILL.md) (or the front door's
`schedule defaults`), which validates each plan with `schedule-plan`. Each run is
unattended, so consequential operations are denied and its prompt asks for file tools
(a command or fetch that needs an approval would stall it); it proposes and reports, and
the user decides in a later, attended chat. Pick times when the machine is usually on: a
laptop that sleeps at night misses night runs.

## Weekly maintenance

- Schedule: `0 13 * * 5` (Fridays at 13:00), or the user's choice.
- Plan: `schedule-plan --app <claude|codex|antigravity> --role researcher --repo <Tinker checkout> --cron "0 13 * * 5" --task "<task>"`
- Task: Weekly maintenance of this Tinker checkout. Read the last 7 days of retros in
  .tinker/retros, open checkpoints in .tinker/tasks, knowledge candidates and the newest
  live eval result. Revalidate notes against current source and mark disproved ones
  stale per policies/knowledge.md. Propose at most three delta edits per
  policies/learning.md, each with evidence, destination and live eval case, and the
  30-day rework rate (retros with `round` > 1), in .tinker/reports/weekly-<date>.md.
  Commit nothing.

In Claude Code, also consolidate the host's own auto memory for this project when the
`consolidate-memory` skill is available: merge duplicates, drop facts current source
contradicts and list up to three that other hosts need. Add that sentence to the task
only for a Claude plan: auto memory reaches no other host.

## Monthly upgrade scan

- Schedule: `15 12 1 * *` is not in the supported cron subset; use `15 12 * * 1` (Mondays
  at 12:15) and let the task skip unless it is the first Monday of the month.
- Plan: `schedule-plan --app <claude|codex|antigravity> --role researcher --repo <Tinker checkout> --cron "15 12 * * 1" --task "<task>"`
- Task: Skip unless it is the month's first Monday. Compare installed Claude Code, Codex
  and Graphify with their latest releases. Recheck docs/providers.md's hook and tool docs
  against TOOL_KINDS in scripts/tinker_runtime.py and the installer matchers, and the
  provider's models, prices and prompting guidance against role tiers and skills. Report
  each discrepancy and each feature that could replace Tinker code or cut cost, with URL
  and date, in .tinker/reports/upgrade-<date>.md. Change nothing else.

The next learn pass reads that report. For a Claude plan, add to the task: "Fetch only
from sites that .claude/settings.json allows." A fetch that needs an approval stalls an
unattended run, so approve the scan's sites in the project settings or on the task's
first attended run.

## Daily graph refresh

Only for repositories whose `## Agent playbook` says `Graph: auto`: one plan per
repository keeps its baseline current, so the refresh at task start stays incremental.

- Schedule: `30 12 * * 1-5` (weekdays at 12:30), or the user's choice.
- Plan: `schedule-plan --app <claude|codex|antigravity> --role engineer --repo <repository> --cron "30 12 * * 1-5" --task "<task>"`
- Task: Refresh this repository's Graphify baseline on its playbook's base branch with
  scripts/graphify_project.py from the Tinker checkout, in the foreground (a background
  command in a scheduled run may never report back), only if the primary checkout is
  clean and on that branch; otherwise report why it was skipped. Fetch nothing; change
  no product files. If the gate denies the command, report the denial.

## Creating one in each host

- Claude Code: `create_scheduled_task` with `taskId` = the plan's `task_id`, its `prompt`
  and `description`, and `cronExpression` = its `cron`. Pass `notifyOnCompletion` only as
  the user chose; when updating a task, omit it so an existing notification choice is kept.
- Codex: `automation_update` with kind `cron`, the plan's `description` as its name, its
  `prompt` and `rrule`, and the repository as its target. Keep the user's notification
  settings in the app.
- Antigravity: manual. Give the user the plan's `cron` and `prompt` for Scheduled Tasks;
  its scheduled runs are unverified.
