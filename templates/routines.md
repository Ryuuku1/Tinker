# Scheduled runs

Create a schedule only when the user asks (the front door's `schedule <what> <when>`).
Each run is unattended, so consequential operations are denied and its prompt asks
for file tools (a command or fetch that needs an approval would stall it); it reports,
and the user decides in a later, attended chat. Pick times when the machine is
usually on: a laptop that sleeps at night misses night runs. A schedule keeps the
prompt it was created with; update it to adopt a change here.

## Plan and create one

1. Agree on the role (a charter in `roles/`), the absolute repository path, the task
   and a schedule `minute hour * * weekdays`, such as `0 7 * * 1-5`.
2. Run the plan line with `python "<root>/scripts/tinker_runtime.py"` in front, such as
   `schedule-plan --app <claude|codex|antigravity> --role <role> --repo <path> --cron "<cron>" --task "<task>"`.
   It only reads. If it refuses, report why and stop.
3. Create it with this app's own scheduler, using the plan's fields verbatim:
   - Claude Code: `create_scheduled_task` with `taskId` = the plan's `task_id`, its
     `prompt` and `description`, and `cronExpression` = its `cron`. Pass
     `notifyOnCompletion` only as the user chose; when updating a task, omit it so an
     existing choice is kept. If the tool is not loaded, search for it first.
   - Codex: `automation_update` with kind `cron`, the plan's `description` as its name,
     its `prompt` and `rrule`, status `ACTIVE` and the repository as its target.
   - Antigravity: manual. Give the user the plan's `cron` and `prompt` for Scheduled
     Tasks; its runs are unverified.
4. The plan's marked prompt makes the run unattended: pass it verbatim (Claude Code
   asks about an unmarked schedule, Codex only best-effort). Remove a schedule with the
   same scheduler.

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
