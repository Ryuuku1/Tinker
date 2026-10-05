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
grant by default. Adding a role never expands the worker budget.

## Add a skill

Create `.agents/skills/<unique-name>/SKILL.md`, with `name` matching its folder and
a short `description` identifying when to use it. Keep workflow content focused;
link shared policy instead of copying it. Relative links resolve from the skill
directory. Update the Lead's routing links and the intentional seven-skill package
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

Change behavior against the `regression` cases in `evals/cases.json`; keep `held-out`
cases for acceptance only, and never edit one to make a change pass (a test pins their
digest). Record observed runs, write a suite manifest and run `python evals/suite.py`;
compare two manifests with `python evals/suite.py compare` only when host, model, case
definitions and configuration match. See the [evaluation guide](../evals/README.md).
Structural checks verify packaging, not agent compliance. Keep failed comparisons
visible; changing the accepted baseline cannot turn a regression into evidence of
improvement. Report missing live runs as `not-verified` for each affected host.
Maintenance routines are opt-in prompt templates in [routines](../templates/routines.md).

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

## Change the Buzz kit on both platforms

The optional Buzz kit has twin scripts: `setup.ps1`, `kit.ps1` and `teardown.ps1` for Windows, and `setup.sh`,
`kit.sh` and `teardown.sh` for Linux. Make every change in both, keeping the PowerShell command names in `kit.sh`
so agent replies and canvases that name them (`Copy-AgentWork`) hold on either platform. Shared files (the agent
image, `scripts/`, `roles/`, `channels/`, `agent.env`) serve both unchanged. `tests/test_buzz_kit_bash.py` runs the
kit checks against bash with Docker mocked and fails when the pins, team, channels, setup steps or command names
drift; the PowerShell twins run only where `pwsh` is installed. Users pick their platform with
`python scripts/tinker_platform.py set windows|linux` (stored in the ignored `.tinker/platform.json`).

