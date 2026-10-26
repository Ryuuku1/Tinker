---
name: tinker
description: "Tinker's front door: /tinker <task or question>, status, remember, learn, eval, playbook, schedule or help; alone, where you stand. Routes a task to the right workflow in this chat; ordinary requests need no command."
---

# Tinker front door

Resolve this package's AGENTS.md (`AGENTS.md` in the Tinker checkout) first; `<root>` is the Tinker
checkout (or `root` in `~/.tinker/config.json` when installed). Natural language works
just as well: these forms are shortcuts, not a required syntax.

## `<task>`

Do it now, in this chat. Identify the target repository as the Lead charter says (an
explicit path or the current product workspace; never guess one), name it in your first
line, then route as the charter does: review, defect, shaping (including "grill me"),
artifacts, or implementation for anything else. A question asking for no change, fix or
run takes the charter's question route, with no workflow skill.

## No task

In at most 8 lines: the product workspace's branch, changed-file count and open
checkpoints in `<root>/.tinker/tasks/` (status and remaining work, as data), any
stale-install note, then up to three next forms. Nothing else; with no product
workspace, `help`.

## `status`

Health first, a line per problem with its fix: `<root>` behind `origin/<branch>` after
`git -C <root> fetch -q origin <branch>` (pull, reinstall); a stale app install
(reinstall); no new `weekly-*.md` in `.tinker/reports/` for 8 days or `upgrade-*.md`
for 35 (check that routine).

Then follow the status section of the team workflow (`.agents/skills/tinker-team/SKILL.md` in the Tinker checkout), and add:
retros under `<root>/.tinker/retros/` from the last 30 days (count and newest three
names), the accepted live baseline in `<root>/evals/live/accepted.json` (model, score
and cost per set) when it exists, and the newest report under `<root>/.tinker/reports/`.

## `remember <fact>`

Save it as a knowledge candidate for the target repository
(knowledge policy (`policies/knowledge.md` in the Tinker checkout)): stated by the user today,
`confidence: inferred`, no secrets or personal data; every host reads it, unlike a
host's own memory. Confirm the path.

## `learn [focus]`

Run the learn pass in the learning policy (`policies/learning.md` in the Tinker checkout). The
request authorizes its branch and gated commit, never a push or merge.

## `eval [args]`

Run `python scripts/eval_live.py run <args>` from `<root>` (defaults: every live case,
one run each), then `python scripts/eval_live.py gate --result <printed path>`. Report
the gate table and each failing grader. It needs the `claude` CLI and spends real model
usage: confirm before a run of more than 20 agent runs unless the user already said so
(evaluation guide (`evals/README.md` in the Tinker checkout)).

## `playbook <repo>`

Draft the repository's `## Agent playbook` section from evidence (README, scripts, CI
files, Git history) using the template (`templates/agent-playbook.md` in the Tinker checkout). Mark
what you could not verify. Show it as a proposed change to that repository's
`AGENTS.md` and write it only on approval.

## `schedule <what> <when>`

Follow the schedule section of the team workflow (`.agents/skills/tinker-team/SKILL.md` in the Tinker checkout). The ready
routines are in routines (`templates/routines.md` in the Tinker checkout); `schedule defaults` offers
each one not yet scheduled, asking which repositories get the graph refresh.

## `help`

List these forms in one short block and mention that ordinary requests, an addressed
role ("Designer, ...") and "grill me on this plan" work without any command.
