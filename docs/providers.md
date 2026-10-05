# Native host setup and verification

Open the Tinker checkout in the chosen host (project mode), or install the
optional user-level plugin so the team loads in any project
([below](#optional-user-level-install)). Keep that package root distinct from each
product target. Use existing host authentication and model selection; no SDK,
provider launcher or credentials are installed, and only the opt-in installer
registers a plugin. A denied action stays denied; switching hosts must never bypass that denial.

An explicit graph request or justified broad topology question uses the package's
single Python Graphify helper. All three hosts point to the same canonical skills and
Lead instructions. Starting a request or creating a worktree does not trigger
indexing. A missing or failed graph is reported while source inspection continues.

## Codex

In the desktop app add/open this checkout as the project. In a terminal start
`codex --add-dir <absolute-product-path>` here. Trust the project when appropriate
so project configuration loads. AGENTS.md provides Lead behavior, .agents/skills/
contains seven skills, and .codex/agents/ defines eight native specialists.
The project requests two concurrent helpers; each specialist disables its own
multi-agent tools. Reader roles request read-only sandboxing and disable the shell
feature; writers request workspace-write. No model is pinned.

Inspect available agents, skills and effective permissions. Parent overrides can
alter requested restrictions. Read-only filesystem mode alone does not remove
shell, network or external MCP tools. Where a reader lacks file or web tools,
supply the canonical charter, exact diff or collected sources in the handoff, or
keep the work in the Lead. Do not widen permissions just to make a descriptor run.

Sources: [project instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[skills](https://learn.chatgpt.com/docs/build-skills),
[subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[hooks](https://learn.chatgpt.com/docs/hooks).

## Claude Code

Authenticate with Claude Code's own sign-in flow, then launch
`claude --plugin-dir . --add-dir <absolute-product-path>` in this checkout.
CLAUDE.md imports canonical company instructions. The plugin exposes the same
physical skills; .claude/agents/ supplies eight project specialists. Inspect the
installed host's memory, skills and agent views; restart existing sessions for
discovery of new descriptors.

Reader roles allow only Read, Grep and Glob; they have no web tools, so research
that needs current documentation uses sources the Lead collects. Writers also allow
Edit, Write and Bash, constrained by parent permissions and sole-writer assignment.
No helper descriptor receives Agent, external MCP tools, personal memory, hooks or
model overrides. Installed session hooks still run for helper tool calls.

Loading this checkout as a plugin from another project does not load its root
instructions or project agents; the installed plugin does that through its
session-start context. With the user-level plugin installed, start project mode
without `--plugin-dir .`: a same-named plugin directory may replace the installed
one for that session, and it carries no hooks. The native plugin validator's
warning about root CLAUDE.md is expected: this file loads as project context.

Sources: [imports](https://code.claude.com/docs/en/memory),
[agent allowlists](https://code.claude.com/docs/en/sub-agents),
[plugin paths](https://code.claude.com/docs/en/plugins-reference),
[hooks](https://code.claude.com/docs/en/hooks),
[tools](https://code.claude.com/docs/en/tools-reference).

## Antigravity

Open this checkout as a project. In Customizations inspect the workspace rule,
skills and custom agents. The .agents/rules/tinker.md rule uses
`trigger: always_on` and references `@../../AGENTS.md` relative to the rule file.
Seven skills remain in .agents/skills/; eight descriptors live in .agents/agents/.
These are distinct from the retained Gemini CLI descriptors.

For Antigravity 2.0, confirm this checkout is an active Project folder, then
inspect Project Settings → Customizations for skills and Customizations → Rules
for the workspace rule. In the IDE, use the agent panel's Customizations menu.
For the Antigravity CLI, launch `agy` in this checkout and inspect interactive
`/skills`; `agy -p "<read-only prompt>"` is its one-shot live probe. There is
no documented headless inventory of all loaded rules and skills. A `gemini`
command is Gemini CLI compatibility evidence, not Antigravity verification.

Grant product access through native workspace/permission controls. Readers allow
view_file, grep_search, find_by_name and list_dir with commands off. Writers request
view_file, grep_search, replace_file_content, write_to_file and run_command under
sandbox execution. CLI 1.2.7 retired find_by_name, grep_search and list_dir from the
default baseline but keeps them for custom agents that list them explicitly.
Verify tool names and effective permissions in the installed surface before use;
an unmapped tool name can hang a subagent. If custom workers are unavailable, the
Lead reads canonical charters and continues transparently.

Sources: [rules](https://antigravity.google/docs/rules-workflows),
[skills](https://antigravity.google/docs/skills),
[subagents](https://antigravity.google/docs/subagents),
[hooks](https://antigravity.google/docs/hooks),
[CLI headless mode](https://antigravity.google/docs/cli/headless/),
[CLI reference](https://antigravity.google/docs/cli/reference/),
[CLI changelog](https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md).

## What is enforced where

Hooks exist only when the optional plugin is installed; project mode relies on
instructions and host permissions alone. The pre-tool gate classifies command text and
structured tool input: a guard against mistakes and naive injection, not a sandbox.

| Action | With the installed hooks | Otherwise |
| --- | --- | --- |
| Force or protected-branch push, branch deletion, discarding work, recursive deletion, `gh`/`az` remote changes, publishing, credential changes, remote or encoded scripts, `codex exec`/`resume` | Claude and Antigravity ask; Codex denies with a request id for a typed, single-use approval of that exact operation | Instructions: explicit authorization |
| The same in an unattended (scheduled) run, plus any commit or push | Denied; no grant path | Instructions |
| Writing host hook settings | Asked; refused when it could disable Tinker | Instructions |
| Changing Tinker's runtime, state, plugin or installer | Always refused | Instructions |
| Creating or updating a schedule without the unattended marker | Claude asks; Codex best-effort (`automation_update` is not a documented hook tool); Antigravity `schedule` gated but its arguments are undocumented | Instructions |
| A gated call the gate cannot judge (missing or malformed fields, unknown tool) | Visible restriction (`payload.incomplete`) | Not applicable |
| Attended commits and feature-branch pushes, ordinary edits, tests and builds | Not gated | Instructions and host permissions |
| Messages, MCP and connector tools, web requests, reading secrets, deployment through unclassified tools | Not gated | Instructions and host permissions |
| Helper budget, one writer, no recursion, read-only reviewer | Descriptors request restrictions; parents can override | Delegation policy |
| Checkpoint ownership | Not enforced; hooks only read front matter | Workspace policy |
| Any gated operation in a Buzz-run chat (`BUZZ_*` variables present) | Denied with the Buzz reason, never asked; typed approvals refused ([Buzz](#buzz-optional-team-surface)) | Instructions |
| Buzz relay changes beyond replying: workflows, memory, channels, membership, reactions, repositories, public posts (`buzz.mutate`) | Claude and Antigravity ask, Codex denies with a request id; denied in Buzz-run chats | Instructions |
| A Buzz-run chat writing a checkout another Buzz-run chat writes | Refused (`workspace.owned`), never taken over; buzz-acp sent no SessionEnd in the spike, so records stay until the user releases them | Workspace policy |
| Creating a schedule from a Buzz-run chat | Denied (`schedule.create`), marked or not | Instructions |

## Hook contracts and tool names

Rechecked on 2026-09-26 against each host's hooks documentation (linked above) and,
for Claude Code, the tool schemas of an installed build. `TOOL_KINDS` in
`scripts/tinker_runtime.py` and the matchers in `scripts/install_apps.py` must stay in step.

| Host | Gated tool names | Decision contract used |
| --- | --- | --- |
| Claude Code | `Bash`, `PowerShell`, `Monitor`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, and `mcp__scheduled-tasks__{create,update}_scheduled_task`, also as a plugin's `mcp__plugin_<plugin>_scheduled-tasks__…` | `permissionDecision: ask` prompts; exit 2 with stderr blocks; empty output keeps normal permissions. `CronCreate`/`ScheduleWakeup` are session-only and not gated: their prompts run in the same session under its own restriction |
| Codex | `Bash` and `apply_patch` (input in `tool_input.command`), `automation_update` (undocumented, best-effort) | `ask` is parsed but unsupported (the hook fails and the tool runs), so Codex gets a deny with a request id; exit 2 blocks; empty output is no decision; changed hooks must be trusted again in `/hooks` |
| Antigravity | `run_command`, `write_to_file`, `replace_file_content`, `multi_replace_file_content`, `code_action` (absent from current docs, kept for earlier builds), `schedule` (arguments undocumented: every prompt-named argument must be a non-empty string carrying the marker) | `force_ask` and `deny` as documented; `decision` is documented as required and `{}` is sent for no opinion, which is unverified. `allow` is never sent, so the user's own review is kept |

Typed approvals match only an unchanged retry. A retry that rewrites a field in the
tool input (for example a free-text justification a host adds) needs a new approval:
this fails closed, and whether Codex adds such a field is unverified until a live run.
A chat restricted because its state became unreadable stays restricted; approve the
operation in a new chat, or remove its file under `~/.tinker/state/unattended/`
yourself once you have checked the chat is attended.

## Optional user-level install

Run these yourself in a terminal, never through an agent (the gate refuses it):

```text
python scripts/install_apps.py --dry-run
python scripts/install_apps.py [--app claude|codex|antigravity]
python scripts/install_apps.py --uninstall [--app ...]
```

It writes the hook script to a stable `~/.tinker/runtime/tinker_runtime.py` and a
bundle (charter copy, manifests, hooks, skills, agents) to `~/.tinker/plugin/`,
then registers:

- Claude Code: `claude plugin marketplace add` and `claude plugin install
  tinker@tinker-local --scope user`. Skills appear as
  `/tinker:<skill>`, teammates as `tinker:<role>`. Hooks use exec form.
- Codex: `codex plugin marketplace add` and `codex plugin add`; root `plugin.json`
  declares the hooks and `~/.codex/agents/tinker-<role>.toml` holds the
  teammates. Trust the hooks in `/hooks` after every install. A consequential
  operation is denied with a request id; type `approve <id>` in that chat, then the
  exact call is retried once, unchanged.
- Antigravity: `~/.gemini/config/plugins/tinker/` with the charter as an
  always-on rule, hooks (PreInvocation, PreToolUse, Stop), skills and
  `tinker-<role>` agents. The hook command carries no quotes, so the Python and
  home paths may contain only ASCII letters, digits and `. _ : \ / -`; otherwise the
  installer refuses Antigravity.

`~/.tinker/apps.json` records every file written with its hash, and ownership is
that record alone. Before writing, every unit is checked: an unrecorded or modified
file refuses its unit and the apps that need it. Candidates are staged and validated;
the staged hook must deny a tamper payload through the own shell of each app in the
run and each app already running the shared runtime. Files are replaced behind a
journal that restores the previous files if a replacement fails, and an interrupted
run is recovered by the next one. Codex is re-registered by removing and adding the
plugin: if the add fails, Codex runs without Tinker's hooks until the recorded
recovery command succeeds. Installation is per app and never
atomic across apps: `status` shows each app as current, stale or not activated, with
its registration (`enabled`, `disabled`, `unknown`) and any recovery command. An app
whose settings cannot be read is refused while another Tinker installation might be
enabled there. The installer also refuses an app where another Tinker installation is
enabled, including one that uses this plugin's id or folder without this installer's
records, and it never reads or rewrites a `~/.tinker/apps.json` that it did not write.

Uninstall removes an app's files once its CLI or its own settings show the plugin
gone; the bundle stays while Claude or Codex still registers it. It never deletes
the runtime script: open chats keep running it, and a missing script makes Python
exit 2, which Claude and Codex treat as a block. `apps.json` stays as the runtime's
ownership record. Restart the apps, then delete `~/.tinker` yourself if unwanted.
Scheduled runs start with a marker that makes them unattended. The team skill builds
schedule plans and the host's own scheduler runs them; Antigravity scheduling is
manual and unverified.

## Buzz (optional team surface)

Setup and operations: [integrations/buzz](../integrations/buzz/README.md). All of the evidence
below comes from one spike on 2026-09-26: Buzz `781d39510`, buzz-acp 0.1.0, `claude-agent-acp`
0.81.2 (bundling Claude Code 2.1.280) and `codex-acp` 1.13.1 (bundling codex-cli 0.156.1), run
in Linux containers against a disposable relay.

The host checks drove the real adapter, host CLI, Tinker hooks and permission flow with a scripted
local model endpoint. That exercises the harness, but it is not a model run. Live model acceptance
is `not-verified` for both hosts, because no provider key was available.

| | Claude Code via `claude-agent-acp` | Codex via `codex-acp` |
| --- | --- | --- |
| Instructions from the working directory | AGENTS.md, through CLAUDE.md's import | AGENTS.md |
| Skills | Only with the installed plugin; `.agents/skills` is not listed in project mode | `.agents/skills` in project mode; plugin skills once installed |
| Tinker's hooks under the adapter | The installed plugin's hooks fire (SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest, Stop); turn-one context reaches the model | Never run with the supported install: codex app-server 0.156.1 does not discover plugin hooks. Hooks in `~/.codex/hooks.json` fire once trusted in `/hooks`, but the installer does not write them |
| Permission behavior | buzz-acp answers every permission request `allow_once` in every mode. `dont-ask` is not advertised, so buzz-acp skips it and Claude runs `default`. Before this integration, Tinker's `ask` was auto-approved in every mode, `plan` included; now it is denied. Claude's `permissions.deny` rules hold | `BUZZ_ACP_PERMISSION_MODE` never applies. codex-acp's modes are `read-only`, `agent` and `agent-full-access` (`INITIAL_AGENT_MODE`), and `read-only` still writes the workspace; with `agent-full-access` a tamper write succeeded |
| Writing in Buzz | Yes: gated operations denied, one writer per checkout (two pooled sessions: the second write was refused) | No: read-only by instruction only |
| Live model acceptance | `not-verified` (no `ANTHROPIC_API_KEY`) | `not-verified` (no `OPENAI_API_KEY`; codex-acp needs an API key, not a ChatGPT subscription) |

**Unsupported:**
- **Antigravity:** Buzz has no ACP runtime for it; the pinned source has no mention of it.
- **`buzz-agent`:** no pre-tool hooks; `docs/MCP_DRIVEN_HOOKS.md` lists `PreToolUse` as deferred.

Harness facts every Buzz setup inherits:
- Concurrent channel and thread sessions, including a pool with `--agents 2`, share one working
  directory.
- The default owner-only gate kept a non-owner's direct mention from becoming a prompt. A
  non-owner's earlier thread reply still reached the model verbatim, inside the owner's prompt, as
  `<thread-context>`.
- Agents inherit `BUZZ_PRIVATE_KEY`, `BUZZ_RELAY_URL` and a harness `GIT_CONFIG_*` block.
  `--permission-mode` and `--respond-to` given as flags stay invisible to the agent.
- buzz-acp forces Codex's sandbox network access on.

Tinker detects Buzz by environment variable *names*, never values:
- `BUZZ_PRIVATE_KEY` together with `BUZZ_RELAY_URL` verifies a Buzz run.
- Any other `BUZZ_*` name still restricts the chat, as ambiguous.
- Anyone can set these names, so detection only ever adds restriction.
- A launcher that strips them would go undetected.
- A shell that exports them restricts your native chats too, so unset them there.

**Hook-enforced under Buzz** (Claude with the installed plugin):
- the deny for every gated operation, including commit, push and `buzz.mutate`;
- refusal of typed approvals;
- the tamper refusal;
- one writer per checkout across Buzz-run chats;
- reports of unsafe settings in turn-one context and `status`.

**Instruction-only** (the [Buzz protocol](../integrations/buzz/protocol.md)):
- treating relayed content as data;
- replying in the triggering thread;
- keeping secrets and raw logs out of posts;
- posting elsewhere only on request (`buzz messages send` is not gated);
- an evidence-backed final report;
- a worktree for every writing task;
- Codex's read-only limit.

## Secondary Gemini CLI compatibility

The existing GEMINI.md import and read-only reviewer descriptor remain available.
Gemini CLI is not Antigravity and is outside the three-host verification claim.
No Gemini installation or extension manifest is added.

## Evidence status

Evidence is kept separate per kind; one kind never stands in for another. Local
observations: Codex CLI 0.146.0, Claude Code 2.1.266 and 2.1.280, Antigravity desktop
2.15.1 (observations, not version pins). No host is fully verified until its live
acceptance cases succeed.

| Evidence | Claude Code | Codex | Antigravity |
| --- | --- | --- | --- |
| Descriptor generation | Verified by package tests (no drift). 2026-09-26: `claude plugin validate` (CLI 2.1.274) passed for this checkout and for a bundle and marketplace rendered by the new installer into a disposable home | Package tests only | Package tests only |
| Host discovery | Live 2026-09-23/24: skills and eight agents loaded; plugin validation passed | Desktop task loaded AGENTS.md and skills (2026-09-23); CLI 0.146.0 present, not run live | Not verified (no scoped live interface, no `agy` on PATH on 2026-09-26) |
| Tool restrictions | Requested by descriptors; not verified live | Same | Same |
| Hook behavior | Live 2026-09-24 for the runtime before this refactor (context, ask, block in default and bypass modes, session end). The 2026-09-26 runtime: sample-payload tests, plus hooks, deny and context under `claude-agent-acp` with a scripted model ([Buzz](#buzz-optional-team-surface)) | Documented formats and shell self-tests only | Documented formats and `cmd /c` self-tests only |
| Task execution | Behavioral cases not verified; no accepted baseline | Not verified (a delegation probe timed out; see below) | Not verified |
| Under Buzz (`buzz-acp`) | Hooks and deny verified with a scripted model; live `not-verified` ([Buzz](#buzz-optional-team-surface)) | Hooks do not run with the supported install; read-only; live `not-verified` | Unsupported |

Earlier Codex notes: a read-only smoke run recognized the Lead, roles, skills and
limits from project context; a disposable feature/delegation probe timed out after
240 seconds without changing its target; a smaller delegation probe exited 0 without
enough native worker detail to verify the team case. Windows checks do not establish
macOS or Linux behavior. See the [evaluation guide](../evals/README.md); preserve
failures and missing capabilities. Use a [checkpoint](../templates/job.md) after the
old host and helpers stop or pause.
