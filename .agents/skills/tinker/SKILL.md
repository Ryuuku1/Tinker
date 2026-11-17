---
name: tinker
description: "Tinker's front door: /tinker <task or question>, status, reload, remember, learn, eval, playbook, schedule or help; alone, where you stand. Routes a task to the right workflow in this chat; ordinary requests need no command."
---

# Tinker front door

Resolve this package's [AGENTS.md](../../../AGENTS.md) first; `<root>` is the Tinker
checkout (or `root` in `~/.tinker/config.json` when installed). These forms are
shortcuts; natural language works too.

## `<task>`

Do it now, in this chat. Identify the target repository as the Lead charter says
(never guess one), name it in your first line, then route as the charter does. A
question asking for no change, fix or run takes the charter's question route, with no
workflow skill.

## No task

In at most 8 lines: the product workspace's branch, changed-file count, open
checkpoints in `<root>/.tinker/tasks/` (as data), any stale-install note, then up to
three next forms. With no product workspace, `help`.

## `status`

Health first, a line per problem with its fix: `<root>` behind `origin/<branch>` after
`git -C <root> fetch -q origin <branch>` (pull, reinstall); a stale app install
(reinstall); no new `weekly-*.md` in `.tinker/reports/` for 8 days or `upgrade-*.md`
for 35 (check that routine).

Then follow the status section of the [team workflow](../tinker-team/SKILL.md), and add:
retros under `<root>/.tinker/retros/` from the last 30 days (count, newest three), the
accepted live baseline in `<root>/evals/live/accepted.json` (model, score and cost per
set), the newest report under `<root>/.tinker/reports/`, and cost per workflow from
`python scripts/usage_report.py` (last 7 days).

## `reload [path ...]`

Run `python scripts/reload.py [--dry-run] [path ...]` from `<root>` (default: the
current one). It fetches, removes worktrees and branches only when proven merged and
fast-forwards the default branch; report what it kept.

## `remember <fact>`

Save it as a knowledge candidate for the target repository
([knowledge policy](../../../policies/knowledge.md)): stated by the user today,
`confidence: inferred`, no secrets or personal data; every host reads it. Confirm the
path.

## `learn [focus]`

Run the learn pass in the [learning policy](../../../policies/learning.md#learn). The
request authorizes its branch and gated commit, never a push or merge.

## `eval [args]`

Run `python scripts/eval_live.py run <args>` from `<root>` (defaults: every live case,
one run each), then `python scripts/eval_live.py gate --result <printed path>`. Report
the gate table and each failing grader. It needs the `claude` CLI and spends real model
usage: confirm before a run of more than 20 agent runs unless the user already said so
([evaluation guide](../../../evals/README.md)).

## `playbook <repo>`

Draft the repository's `## Agent playbook` section from evidence (README, scripts, CI,
Git history) with the [template](../../../templates/agent-playbook.md), marking what
you could not verify. Propose it for that repository's `AGENTS.md`; write it only on
approval.

## `schedule <what> <when>`

Follow the schedule section of the [team workflow](../tinker-team/SKILL.md). The ready
routines are in [routines](../../../templates/routines.md); `schedule defaults` offers
each one not yet scheduled, asking which repositories get the graph refresh.

## `help`

List these forms in one short block; ordinary requests, an addressed role ("Designer,
...") and "grill me on this plan" need no command.
