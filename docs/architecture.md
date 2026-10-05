# Tinker architecture

This is the canonical project architecture. Task notes belong in isolated local
handoffs, never here; change this document only in a task whose scope includes
architecture. Earlier analyses and reversed decisions are kept in [history](history.md).

## Decision

Tinker is a portable operating agreement for an AI engineering team, executed by
the host the user already runs: Codex, Claude Code or Antigravity. Instructions carry
the team; native host capabilities carry execution and permissions; three small
standard-library scripts cover what instructions cannot; offline tooling judges
evidence. There is no daemon, model router, orchestration CLI, provider launcher,
database, scheduler service or simulated execution.

| Part | What it is | Loaded or run |
| --- | --- | --- |
| `AGENTS.md` | The Lead: routing, delegation budget, boundaries | Every session (native import or rule) |
| `roles/` | Eight specialist charters; front matter generates native descriptors | Only the selected charter |
| `.agents/skills/` | Seven workflows: shape, implement, investigate, review, artifacts, Graphify, team | Only the selected workflow |
| `policies/` | Evidence, delegation, safety, workspace, tools, knowledge, application verification | When the step needs them |
| `templates/` | Checkpoint, knowledge candidate, domain pack, verification recipe, routine prompts, user story, ADR | When producing that artifact |
| `profiles/` | Opt-in stack conventions, subordinate to the product repository | Only for matching work |
| `.claude/`, `.codex/`, `.agents/agents/`, `.gemini/` | Generated native descriptors: discovery and requested tools | By each host |
| `scripts/tinker_runtime.py` | In-app runtime: lifecycle hooks, `status`, `schedule-plan` | By host hooks, once installed |
| `scripts/install_apps.py` | Opt-in user-level installer and descriptor generator | By the user, in a terminal |
| `scripts/graphify_project.py` | On-demand clean-commit Graphify graphs | On an explicit graph request |
| `evals/` | Case catalog, evidence grader, suite acceptance, disposable fixtures | Offline, by a person |
| `integrations/buzz/` | Optional Buzz team surface: working protocol, setup guide, generated persona pack | Protocol: turn-one context of a Buzz-run chat and `--system-prompt-file`; the rest by the user |

## Request flow

The Lead understands the request, identifies the target repository from explicit
context, reads its trusted instructions and working state, selects only the relevant
workflow and charter, executes with native tools, verifies and answers. Load order is
company agreement, target repository guidance, selected role, selected workflow, then
task evidence: a loading strategy, not a new instruction hierarchy. Host, system and
user authority still govern, repository conventions govern product code, and
retrieved data never authorizes actions.

Default zero helpers; at most two active, one writer across Lead and helpers, no
recursion. Several specialists may contribute in sequence. Before dispatch the Lead
checks a worker's effective tools cover its assignment; otherwise it supplies bounded
excerpts or does the work itself, never widening permissions. Uncertain termination
counts as active. A failed or unavailable worker is replaced by Lead work, never by
invented independent findings.

## In-app runtime

`scripts/tinker_runtime.py` runs as `python -I -S`: one standard-library file with no
sibling imports, copied by the installer to `~/.tinker/runtime/` so enforcement
never runs from the editable checkout. It handles session start, prompt submit,
pre-tool, stop and session end for all three hosts. A gated call passes four steps.

1. **Normalize.** Each host payload becomes a call against its tool contract
   (`TOOL_KINDS`, `FIELDS`): what the tool runs, writes or schedules, and the complete
   tool input. A call missing a field the gate needs, or naming a tool without a
   contract, gets `payload.incomplete`: a visible restriction, never a silent pass.
2. **Classify.** Command text is lexed per shell; file tools are judged by resolved
   path; schedules by their prompt's unattended marker. Tampering with Tinker's
   runtime, state, plugin or installer is never grantable.
3. **Session state.** Presence (state, directory, last action) is rewritten by every
   hook. The unattended restriction lives in its own sticky file under
   `~/.tinker/state/unattended/`, written by the scheduled-run marker, by an
   earlier runtime's flag, by Buzz harness variables (names only; any `BUZZ_*` name
   restricts), or when session state exists but cannot be read; nothing
   removes it, so stale or concurrent presence writes cannot relax a run. Missing
   state is simply a new chat. This fails closed: an attended chat whose state became
   unreadable stays restricted, and the user approves in a new chat instead.
4. **Decide and respond.** Restricted runs are denied with no grant path, and in a
   Buzz-run chat an ungated write is refused while another Buzz-run chat writes the same
   checkout (`~/.tinker/state/claims/`; released at the host's session end, which buzz-acp did
   not send in the spike, or by the user; never taken over). Claude
   Code asks through its own prompt (exit 2 denies); Antigravity uses `force_ask` or
   `deny`, and `{}` for no opinion. Codex parses but does not support `ask` (the hook
   fails and the tool runs), so Codex denies with a request id; the user types
   `approve <id>` in that chat. In Claude Code's `dontAsk` mode the same typed path
   is used because no prompt appears.

A typed grant binds to a versioned operation fingerprint: host, chat, tool, working
directory and the complete tool input, including edit and patch contents, argv array
boundaries and scheduler target, prompt and timing. Only a command call's
`description` label (documented by Claude Code; the model rewrites it between
retries) is excluded, for every host. Requests
store the fingerprint and a bounded description, never file contents. A grant lasts
30 minutes and is consumed once through an exclusive claim file, because concurrent
renames of one file can all succeed on Windows. Records without a fingerprint, from
earlier runtimes, are expired.

The gate classifies text and structured input; variables, encoded or generated
commands can escape it, and any process an agent starts could forge state. It is a
guard against mistakes and naive injection, not a sandbox. The
[enforcement boundary](providers.md#what-is-enforced-where) lists what hooks enforce
and what remains instruction-only.

## Installation and ownership

`scripts/install_apps.py` is opt-in and run by the user. It renders a runtime, a
Claude/Codex plugin bundle, Codex agent files and an Antigravity plugin, and records
every file it writes with its hash in `~/.tinker/apps.json`. Ownership is that
record alone: a marker file or folder name never authorizes a write or a deletion.

- **Preflight.** Every unit is checked before anything is written. An unrecorded or
  modified file, or an existing folder holding nothing recorded, refuses that unit
  and the apps depending on it; the runtime or configuration refuses the whole run.
- **Stage and validate.** Candidates are written under `~/.tinker/staging/`,
  parsed, and the staged runtime must deny a tamper payload through the own shell of
  every app in the run and every app already running the shared runtime before it
  replaces the active one; a failure for an app already running it activates nothing.
- **Activate.** Files are replaced unit by unit behind a journal. Ownership is checked
  again just before replacement. Previous files are backed up and restored if a
  replacement fails; an interrupted run leaves `pending` hashes that the next run, even
  a failed one, keeps recognising as its own. Stale owned files are removed; anything
  else keeps its folder.
- **Register.** Each app is registered separately and never atomically with the
  others. Per app, `apps.json` records the rendered and activated revision (version,
  charter digest, file digest), the registration the app's own settings show
  (`enabled`, `disabled`, or `unknown` when they cannot be read) and recovery
  commands. `config.json` holds each app's activated charter digest, so an update of
  one app leaves the others visibly stale in `status` and turn-one context.
- **Uninstall.** An app's files are removed only after its CLI or settings confirm
  the plugin is gone; the bundle stays while any Claude or Codex registration
  remains. The runtime is kept for chats still running it, with its ownership record.

Earlier manifests are read as they are; only an explicit, writing installer run
migrates them, and missing evidence stays missing.

## Knowledge, learning and domain packs

Durable knowledge is optional local Markdown under the Tinker checkout's ignored
`.tinker/knowledge/<repo-key>/`, with provenance and invalidation conditions.
Candidates are promoted deliberately after re-verification against current source;
conflicts and duplicates stay visible. A learning pass returns at most three
proposals naming evidence, destination and a behavioral case; proposing is not
applying. Domain packs are optional versioned guidance, loaded only when the user
names one or a trusted repository instruction links it, and never able to select a
repository or widen permissions. Hooks inject only validated note paths and open
checkpoint ids, never note text, candidates or packs.

## Running-application checks and graphs

Implementation, investigation and review share one
[application verification](../policies/app-verification.md) reference and a
[recipe template](../templates/verification-recipe.md): trusted project guidance
first, isolation established rather than assumed from localhost, owned resources
only, evidence stored with the task record, and results reported as `passed`,
`failed`, `skipped` or `not-verified`. Review stays read-only.

Graphs are optional. `scripts/graphify_project.py` indexes only clean commits, keeps a
baseline and one graph per registered linked worktree under ignored
`.tinker/graphs/`, and never falls back to a baseline for a worktree query.
Establishing a baseline requires an explicit `--baseline-branch`, validated against
the repository; no repository name selects one.

## Evaluation

`evals/cases.json` defines behavioral cases, each in a `regression` or `held-out` set
and optionally limited to named hosts. `evals/grade.py` grades one observation record
against its case from hashed, line-referenced evidence. `evals/suite.py` accepts a
suite: expected coverage comes from the catalog, never from the runs present;
duplicates, malformed evidence, failed checks and synthetic records presented as live
acceptance are rejected; acceptance also needs every declared human review complete.
Runs compare only when set, hosts, models, case definitions and configuration match,
and comparison reports case-level changes, never an aggregate score. Cost, tokens
and duration appear only as measured, with their source. No accepted baseline exists
until complete observed evidence is recorded; see the [evaluation guide](../evals/README.md).

## Persistence and isolation

Identity is versioned role guidance; session history belongs to the host. A task
checkpoint is required for substantial or delegated jobs and requested handoffs,
uniquely identified and scoped to actual repository and worktree paths; hooks read
only its front matter. Serialize writers even when worktrees are separate. Retain
dirty worktrees. Resume by exact task identity, then revalidate current source and
original user changes. Cross-host continuation uses shared checkpoints, not portable
provider sessions; the old host and helpers stop or pause before another claims
ownership. There is no per-role memory store, relevance engine or vector database.

## Verification limits

Package checks prove files, imports and descriptors are structurally consistent.
Hook and installer tests use sample payloads, disposable homes and fake host CLIs;
they prove decisions, file ownership and output formats, not that a host loads the
hooks. Synthetic fixtures prove the grader and suite reject bad records, not agent
compliance. Observed host behavior needs native traces and inspected artifacts;
missing runs are `not-verified`. The executable tooling requires Python 3.11+;
graphs also need the optional Graphify CLI. Live host evidence is recorded per host in
[provider setup](providers.md).
