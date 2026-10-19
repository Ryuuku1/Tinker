---
name: tinker
description: "Tinker's front door: /tinker <task>, status, learn [focus], eval [args], playbook <repo>, schedule <what> <when> or help. Routes a task to the right workflow in this chat; ordinary requests need no command."
---

# Tinker front door

Resolve this package's [AGENTS.md](../../../AGENTS.md) first; `<root>` is the Tinker
checkout (or `root` in `~/.tinker/config.json` when installed). Natural language works
just as well: these forms are shortcuts, not a required syntax.

## `<task>`

Do it now, in this chat. Identify the target repository as the Lead charter says (an
explicit path or the current product workspace; never guess one), name it in your first
line, then route as the charter does: review, defect, shaping (including "grill me"),
artifacts, or implementation for anything else.

## `status`

Follow the status section of the [team workflow](../tinker-team/SKILL.md), then add:
retros under `<root>/.tinker/retros/` from the last 30 days (count and newest three
names), the accepted live baseline in `<root>/evals/live/accepted.json` (model, score
and cost per set) when it exists, and the newest report under `<root>/.tinker/reports/`.

## `learn [focus]`

Run the learn pass in the [learning policy](../../../policies/learning.md#learn). The
request authorizes its branch and gated commit, never a push or merge.

## `eval [args]`

Run `python scripts/eval_live.py run <args>` from `<root>` (defaults: every live case,
one run each), then `python scripts/eval_live.py gate --result <printed path>`. Report
the gate table and each failing grader. It needs the `claude` CLI and spends real model
usage: confirm before a run of more than 20 agent runs unless the user already said so.
See the [evaluation guide](../../../evals/README.md).

## `playbook <repo>`

Draft the repository's `## Agent playbook` section from evidence (README, scripts, CI
workflow files, Git history and branches) using the
[template](../../../templates/agent-playbook.md). Mark what you could not verify. Show
it as a proposed change to that repository's `AGENTS.md` and write it only on approval.

## `schedule <what> <when>`

Follow the schedule section of the [team workflow](../tinker-team/SKILL.md). The ready
routines are in [routines](../../../templates/routines.md); `schedule defaults` offers
each one not yet scheduled, asking which repositories get the graph refresh.

## `help`

List these forms in one short block and mention that ordinary requests, an addressed
role ("Designer, ...") and "grill me on this plan" work without any command.
