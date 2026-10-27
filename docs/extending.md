# Extend and upgrade

Keep one source per rule. Common ownership/routing belongs in `AGENTS.md`, reusable
constraints in the relevant policy, expertise in a role, repeatable workflow in a
skill. The .NET profile is opt-in. Do not copy company rules into every file.

## Add a role

First identify its distinct authority, tools, context, expertise or independence.
If it merely rephrases another role, use an assignment of that role instead.
Add a concise Markdown charter under `roles/` with front matter `description` and
`access: read|write`, and a discoverable link in the delegation section. Native
descriptors are generated from that front matter for all three primary hosts: the
user runs `python scripts/install_apps.py --write-descriptors` in a terminal (the
installed gate refuses the installer inside an agent); tests fail on drift.
Never hand-edit a generated descriptor. Do not add a model, personal memory or MCP
grant by default. The one exception is `tier: light` (read roles only, as the
Explorer uses): Claude runs that helper on its small model at low effort without
`CLAUDE.md`, and every host gives it only its own charter, so keep such a role to plain
search. Adding a role never expands
the worker budget.

## Add a skill

Create `.agents/skills/<unique-name>/SKILL.md`, with `name` matching its folder and
a short `description` identifying when to use it. Keep workflow content focused;
link shared policy instead of copying it. Relative links resolve from the skill
directory. Update the Lead's routing links and the intentional eight-skill package
check only when the new workflow genuinely deserves expansion. The Claude manifest
already points at the canonical parent directory.

Create behavioral cases with observable outcomes, then test them on a disposable
repository. Structural checks are necessary but not behavioral proof. Run:

```text
python -m unittest discover -s tests -v
claude plugin validate --json .
```

## Gate another tool

Add the tool to `TOOL_KINDS` and, for the fields the gate needs to judge it,
`FIELDS` in `scripts/tinker_runtime.py`, then to the same app's matcher in
`scripts/install_apps.py`, citing the host documentation or tool schema that names
it. Add sample-payload tests for a consequential call, a benign one and an incomplete
one. A tool the matcher sends without a contract gets a visible restriction, so the
two lists must change together. Live behavior stays `not-verified` until observed.

## Add facts about one project

Project facts never go into this package. Put them in that project's own `AGENTS.md`
(or `CLAUDE.md`) under `## Agent playbook`, following the
[template](../templates/agent-playbook.md): base branch, gate commands, commit style,
worktrees, a live-pass recipe, `Graph: auto|on-demand` and pitfalls. Ask
`tinker playbook <path>` to draft it from evidence. Keep bullets verified and short,
and change one bullet at a time; the learn pass proposes such bullets but writes them
only on your approval in that project.

## Add a domain pack or a verification recipe

A domain pack is optional guidance for one domain, built from the
[domain pack template](../templates/domain-pack.md). Keep organization-specific packs
in that organization's repository or a local folder, and link one from a product
repository's own instructions when that repository should always use it; otherwise
the user names it in a request. Never add a pack to this package's core, and never
let a pack choose a repository or widen permissions.
Read selected guidance for questions too; selecting a pack does not require a
software workflow, a particular provider or a repository registry.

A verification recipe records how to run and check one application flow
([recipe template](../templates/verification-recipe.md)). Prefer the project's own
scripts and documentation; keep filled recipes with the task record, never in the
product repository unless the project asks for one as a reviewable change.

## Evaluate a change

For Claude Code, measure behavior with the live cases first. A case is a folder
`evals/live/<name>/` with a `case.yaml` (prompt, allowed tools, graders, and exactly
one of the tags `regression` or `heldout`) and a `setup.sh` that builds its workspace
with the helpers in `evals/live/_shared/workspace.sh`. Add or tighten a `regression`
case when a change alters behavior no case covers, and see it fall short without the
change first; never edit a `heldout` case to fit a change. Iterate with `python scripts/eval_live.py run --case <name> --runs 1`, then
run the regression and held-out sets and `python scripts/eval_live.py gate --result
<path>`; commit `evals/live/accepted.json` with the change when you accept a new
baseline. `tests/test_eval_live.py` checks every case's structure and scaffold without
a model. The learn pass follows the same rules automatically
([learning policy](../policies/learning.md)).

For every host, change behavior against the `regression` cases in `evals/cases.json`; keep `held-out`
cases for acceptance only, and never edit one to make a change pass (a test pins their
digest). Record observed runs, write a suite manifest and run `python evals/suite.py`;
compare two manifests with `python evals/suite.py compare` only when host, model, case
definitions and configuration match. See the [evaluation guide](../evals/README.md).
Structural checks verify packaging, not agent compliance. Keep failed comparisons
visible; changing the accepted baseline cannot turn a regression into evidence of
improvement. Report missing live runs as `not-verified` for each affected host.
Maintenance routines (weekly maintenance, monthly upgrade scan, daily graph refresh)
are opt-in prompt templates in [routines](../templates/routines.md).

## Upgrade safely

Keep the package checkout separate from product source and local knowledge. Inspect
the update diff, preserve any local modifications and deliberately integrate the
new version using ordinary Git tools. The only installer is the opt-in
`scripts/install_apps.py`: it registers a plugin through each app's own CLI,
records what it wrote with hashes and never replaces or deletes a file that record
does not cover. Re-run it after an upgrade to refresh the installed copy, for every
app you use: hooks and `status` show each app that is still stale.
Never run anything that overwrites product instruction files. Review native
adapter changes against the installed host's documentation; re-run package checks.

Local `.tinker/` knowledge/checkpoints are ignored and must not be overwritten
by package upgrades. If moving to a fresh checkout, selectively migrate needed
notes, revalidate their repository identity/provenance and retain the old copy
until the move is confirmed. Do not blindly copy credentials or machine settings.

## Debug behavior

Inspect the host's loaded instruction/skill view, actual worker IDs, tool calls,
command results and final diff. Ask for a short account of the selected workflow,
sources used, checks and permission limits; do not request private reasoning.
Distinguish discovery failure, unavailable capability, denied access and an agent's
bad decision. Add only the smallest demonstrated correction and a relevant case.
No new routine, hook, script or abstraction without a repeated concrete need. The
in-app runtime's hooks exist for such needs (turn-one context, tool-loop
enforcement, presence); extend them only for the same kind, with a payload test.
