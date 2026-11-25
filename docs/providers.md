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
contains seven skills, and .codex/agents/ defines four native specialists.
The project sets no helper cap of its own (Codex's default applies; the Lead sizes
the team); each specialist disables its own multi-agent tools. Reader roles request read-only sandboxing and disable the shell
feature; writers request workspace-write. No model is pinned.

From Claude Code, the Lead can also run the Codex CLI (`codex exec`) as an external
worker for study, plan or implement work when the user asks for it in plain words
([external workers](../policies/external-workers.md)); the
[evidence](#evidence-status) below separates what was measured from what was not.

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
In the desktop app, the [task start](../policies/workspace.md#task-start) adds each
checkout outside the chat's folders with `request_directory`, so the app shows its
diffs and can link and watch its pull requests; chats without that tool skip it.
CLAUDE.md imports canonical company instructions. The plugin exposes the same
physical skills; .claude/agents/ supplies four project specialists. Inspect the
installed host's memory, skills and agent views; restart existing sessions for
discovery of new descriptors.

Reader roles allow only Read, Grep and Glob; they have no web tools, so research
that needs current documentation uses sources the Lead collects. Writers also allow
Edit, Write and Bash, constrained by parent permissions and sole-writer assignment.
No helper descriptor receives Agent, external MCP tools, personal memory or hooks.
The one model setting is a cost hint: the search-only Explorer (`tier: light` in its
charter) runs on `haiku` and reads only its own charter; every other descriptor uses
the session's model. Installed session hooks still run for helper tool calls.

Chats opened in this checkout also load `.claude/settings.json`: deny rules for
destructive Git through both the Bash and PowerShell tools (force or mirror pushes,
`reset --hard`, `clean`, `restore`, discarding checkouts and switches, forced branch
deletion, `stash clear` (a single `stash drop` is allowed), forced worktree removal, ref and reflog deletion,
`gc --prune=now`), no ask rules (Claude Code shows an ask rule's prompt even in
bypass mode, where the user chose no prompts), pre-allowed edits under `.tinker/`
(retros, tasks, reports, evidence, patches), and the official Playwright plugin for
[live passes](../policies/app-verification.md#live-pass-in-a-browser). A remote branch
delete therefore prompts only in default mode, where no rule allows it. Deny rules
hold in every permission mode, including bypass; the installed hook gate covers
other projects, and in bypass and auto modes it asks nothing and denies only tampering with
Tinker's state and unattended runs. Install the browser plugin once with
`claude plugin install playwright@claude-plugins-official`. Project settings do not
reach chats opened elsewhere, so add the same `env` block to `~/.claude/settings.json`
for live passes there, with an absolute output folder inside this checkout:

```json
"env": {
  "PLAYWRIGHT_MCP_ISOLATED": "true",
  "PLAYWRIGHT_MCP_ALLOWED_ORIGINS": "http://localhost:*;https://localhost:*;http://127.0.0.1:*;https://127.0.0.1:*",
  "PLAYWRIGHT_MCP_OUTPUT_DIR": "<absolute Tinker checkout>/.tinker/playwright",
  "PLAYWRIGHT_MCP_CAPS": "network"
}
```

To test a non-local URL you name in the chat, create a storage state yourself
(`npx playwright open --save-storage <path outside every repository> <url>`, log in,
close), then set `PLAYWRIGHT_MCP_STORAGE_STATE` and add the origin in
`.claude/settings.local.json`; remove both afterwards. Tinker never types credentials.

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
Seven skills remain in .agents/skills/; four descriptors live in .agents/agents/.
These are distinct from the retained Gemini CLI descriptors.

For Antigravity 2.0, confirm this checkout is an active Project folder, then
inspect Project Settings → Customizations for skills and Customizations → Rules
for the workspace rule. In the IDE, use the agent panel's Customizations menu.
For the Antigravity CLI, launch `agy` in this checkout and inspect interactive
`/skills`; `agy -p "<read-only prompt>"` is its one-shot live probe. There is
no documented headless inventory of all loaded rules and skills. A `gemini`
command is Gemini CLI compatibility evidence, not Antigravity verification.

From Claude Code, the Lead can also run the Antigravity CLI (`agy -p`) as an external
worker when the user asks for it in plain words, pinned for now to the model and
effort the user named ([external workers](../policies/external-workers.md#antigravity)).
The installed gate asks for an `agy` run as it does for `codex exec`; the
[evidence](#antigravity-cli-as-an-external-worker) below separates what was measured
from what was not.

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
| Force or protected-branch push, branch deletion, discarding work, recursive deletion, `gh`/`az` remote changes, publishing, credential changes, remote or encoded scripts, `codex exec`/`resume`, an `agy` run (`-p`, `-i`, `--continue`, `--resume`) | Claude and Antigravity ask; Codex denies with a request id for a typed, single-use approval of that exact operation | Instructions: explicit authorization |
| The same in an unattended (scheduled) run, plus any commit or push | Denied; no grant path | Instructions |
| Writing host hook settings | Asked; refused when it could disable Tinker | Instructions |
| Changing Tinker's runtime, state, plugin or installer | Always refused | Instructions |
| Creating or updating a schedule without the unattended marker | Claude asks; Codex best-effort (`automation_update` is not a documented hook tool); Antigravity `schedule` gated but its arguments are undocumented | Instructions |
| A gated call the gate cannot judge (missing or malformed fields, unknown tool) | Visible restriction (`payload.incomplete`) | Not applicable |
| Attended commits and feature-branch pushes, ordinary edits, tests and builds | Not gated | Instructions and host permissions |
| A test, build or lint run whose output stream exceeds 200 lines | Claude: that stream reaches the model as its failures and last 30 lines, and the full output is saved under the temp folder's `tinker-logs/`. Codex and Antigravity: unchanged | `python scripts/filter_test_log.py` by hand |
| Messages, MCP and connector tools, web requests, reading secrets, deployment through unclassified tools | Not gated | Instructions and host permissions |
| Helper budget, one writer, no recursion, read-only reviewer | Descriptors request restrictions; parents can override | Delegation policy |
| Checkpoint ownership | Not enforced; hooks only read front matter | Workspace policy |

## Hook contracts and tool names

Rechecked on 2026-09-26 against each host's hooks documentation (linked above) and,
for Claude Code, the tool schemas of an installed build. `TOOL_KINDS` in
`scripts/tinker_runtime.py` and the matchers in `scripts/install_apps.py` must stay in step.

| Host | Gated tool names | Decision contract used |
| --- | --- | --- |
| Claude Code | `Bash`, `PowerShell`, `Monitor`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, and `mcp__scheduled-tasks__{create,update}_scheduled_task`, also as a plugin's `mcp__plugin_<plugin>_scheduled-tasks__…` | `permissionDecision: ask` prompts; exit 2 with stderr blocks; empty output keeps normal permissions. `CronCreate`/`ScheduleWakeup` are session-only and not gated: their prompts run in the same session under its own restriction. `PostToolUse` on `Bash` and `PowerShell` returns `updatedToolOutput` in the documented Bash shape (`stdout`, `stderr`, `interrupted`, `isImage`, with a long runner stream trimmed); Claude ignores a value that does not match the tool's schema and keeps the original, as it does for empty output |
| Codex | `Bash` and `apply_patch` (input in `tool_input.command`), `automation_update` (undocumented, best-effort) | `ask` is parsed but unsupported (the hook fails and the tool runs), so Codex gets a deny with a request id; exit 2 blocks; empty output is no decision; changed hooks must be trusted again in `/hooks` |
| Antigravity | `run_command`, `write_to_file`, `replace_file_content`, `multi_replace_file_content`, `code_action` (absent from current docs, kept for earlier builds), the CLI's `write_file` and `edit_file` (agy 1.5.17 sends the target in `Path`; `edit_file`'s other arguments not seen), `schedule` (arguments undocumented: every prompt-named argument must be a non-empty string carrying the marker) | `force_ask` and `deny` as documented; `decision` is required, and `allow` is sent for no objection: the documentation says it delegates to the next hook or the default policy, and agy 1.5.17 still refused a write outside its workspace after it (2026-11-25). `{}` is not sent: agy 1.5.17 reads it as a deny with an empty reason. How the desktop app reads `allow` is not verified |

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
python scripts/install_apps.py --instance <name> [...]   # beside another installation
```

It writes the hook script to a stable `~/.tinker/runtime/tinker_runtime.py` and a
bundle (charter copy, manifests, hooks, skills, agents) to `~/.tinker/plugin/`,
then registers:

- Claude Code: `claude plugin marketplace add` and `claude plugin install
  tinker@tinker-local --scope user`. Skills appear as
  `/tinker:<skill>` (the front door is `/tinker:tinker`), teammates as
  `tinker:<role>`. Hooks use exec form.
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
On such a machine, install [beside it](#beside-another-installation) or run the
checkout in project mode: the runtime ignores the other installation's `config.json`,
takes the checkout as its root, and `status` says whose home it is.

Uninstall removes an app's files once its CLI or its own settings show the plugin
gone; the bundle stays while Claude or Codex still registers it. It never deletes
the runtime script: open chats keep running it, and a missing script makes Python
exit 2, which Claude and Codex treat as a block. `apps.json` stays as the runtime's
ownership record. Restart the apps, then delete `~/.tinker` yourself if unwanted.
Scheduled runs start with a marker that makes them unattended. The front door builds
schedule plans and the host's own scheduler runs them; Antigravity scheduling is
manual and unverified.

### Beside another installation

`--instance <name>` (lowercase letters and digits, at most 20, not `local`) installs
under names the default installation never uses: home `~/.tinker-<name>/`, marketplace
`tinker-<name>`, plugin id `tinker@tinker-<name>` and Antigravity folder
`~/.gemini/config/plugins/tinker-<name>/`. The plugin is still named `tinker`, so its
skills and teammates keep their names. Every rendered hook command carries
`--instance <name>`: the runtime keeps presence, approvals and run outcomes in that
home and guards it, its plugin caches and its plugin id as it guards the default ones,
which stay guarded too. A name the runtime cannot use leaves the default guard running,
never none. The rendered skills point at that home's `config.json` and run
`tinker_runtime.py --instance <name>`; pass the same option to `status`, later
installs and `--uninstall`. The other installation's home, records and registration
are never read as this one's or changed.

Where another Tinker is enabled in an app:

- Claude Code: this one is installed, then turned off with `claude plugin disable
  tinker@tinker-<name> --scope user`. An install turns a plugin on again, so every
  update turns it off again while the other stays enabled; after a switch, updates keep
  this one on. Both on would run two gates and two charters in each chat. To switch,
  disable the other and enable this one at user scope, or for one project put
  `"enabledPlugins": {"tinker@tinker-local": false, "tinker@tinker-<name>": true}` in its
  `.claude/settings.local.json`; the installer prints both. Run them yourself: the guard
  denies an agent's command or edit that changes a Tinker plugin's registration. Checked on 2026-11-17 in an isolated Claude Code configuration: two
  plugins named `tinker` from different marketplaces install side by side, `disable`
  and `enable` switch one at user scope, and a project's `settings.local.json`
  overrides the user setting.
- Codex: its CLI only adds or removes a plugin, so this one stays out of Codex until
  the other is removed; then re-run with `--app codex`. Teammate files
  `~/.codex/agents/tinker-<role>.toml` have the same names in every installation, and
  one the other installation wrote is kept, not replaced.
- Antigravity loads every plugin folder, so it is left out the same way.

## Secondary Gemini CLI compatibility

The existing GEMINI.md import and read-only reviewer descriptor remain available.
Gemini CLI is not Antigravity and is outside the three-host verification claim.
No Gemini installation or extension manifest is added.

## Evidence status

Evidence is kept separate per kind; one kind never stands in for another. Local
observations: Codex CLI 0.146.0 and 0.171.0, Claude Code 2.1.266 and 2.1.280, Antigravity desktop
2.15.1 (observations, not version pins). No host is fully verified until its live
acceptance cases succeed.

| Evidence | Claude Code | Codex | Antigravity |
| --- | --- | --- | --- |
| Descriptor generation | Verified by package tests (no drift). 2026-09-26: `claude plugin validate` (CLI 2.1.274) passed for this checkout and for a bundle and marketplace rendered by the new installer into a disposable home | Package tests only | Package tests only |
| Host discovery | Live 2026-09-23/24: skills and eight agents loaded; plugin validation passed | Desktop task loaded AGENTS.md and skills (2026-09-23); CLI 0.146.0 present, not run live | Not verified (no scoped live interface, no `agy` on PATH on 2026-09-26) |
| Tool restrictions | Requested by descriptors; not verified live | Same | Same |
| Hook behavior | Live 2026-09-24 for the runtime before this refactor (context, ask, block in default and bypass modes, session end). The 2026-09-26 runtime: sample-payload tests. The output trim (2026-11-17): sample-payload tests only, not yet checked in an installed app | Documented formats and shell self-tests only | Documented formats and shell self-tests only (`cmd /c` on Windows, `sh -c` elsewhere) |
| Task execution | Live baseline accepted 2026-11-17 (`evals/live/accepted.json`: regression 0.979 over 28 runs, heldout 0.889 over 5, model opus) | Not verified (a delegation probe timed out; see below) | Not verified |

The Codex CLI as an [external worker](../policies/external-workers.md) from Claude Code.
The smoke tests use a disposable Git repository and a linked worktree per implement
run under the user profile, outside the temp folder (writable in the sandbox), an
outside target path next to them, the policy's commands with effort low and logs in
`<Tinker root>/.tinker/evidence/`; afterwards delete that folder and file, never
force-removing a worktree. They ran on 2026-11-23 on Windows with Codex CLI 0.171.0.

| Evidence | Status |
| --- | --- |
| Flags the recipe uses | Verified 2026-11-22: `codex exec --help` on 0.171.0 lists every flag in the policy's commands; `exec resume` and `exec fork` list no `-s` and no `-C` |
| User config | Verified 2026-11-22: without `--ignore-user-config` the user's config set the model (one the account rejected with HTTP 400 `model_not_found`), sandbox and effort, loaded plugins and printed config and hook warnings as `item.completed` items of type `error`; a `-s read-only` run with an explicit model wrote the requested text to its `-o` file. With the flag the warnings were gone, but that run stopped at the usage limit |
| Windows sandbox key | Verified 2026-11-23: `--ignore-user-config` also drops the user's `[windows] sandbox` setting. Without it the study run's read was rejected in `<run>.err` ("blocked by policy"), with no command item in the JSONL, and the run still passed the success test with a blocked handoff (input 41,746, 20,608 cached). The same brief with `-c windows.sandbox=elevated` ran the read. `codex sandbox` accepts `elevated`, `unelevated` and `mxc` and refuses unknown values; only `elevated` was run through `exec` |
| Sandbox (`codex sandbox -c sandbox_mode=...`, Windows, no model) | Verified 2026-11-22 with the CLI then installed (recorded as 0.146.0), not re-run on 0.171.0; `codex sandbox` loads the user config, here the elevated Windows sandbox: in a linked worktree `workspace-write` wrote in the worktree and the temp folder and was denied elsewhere in the user profile; `read-only` was denied both; `git commit` failed on the main repository's `.git/worktrees/<name>/index.lock`; `cmd` printed errorlevel 0 after "Access is denied" |
| JSONL events | Verified 2026-11-22: `thread.started` (with `thread_id`), `turn.started`, `item.completed` (`agent_message` or `error`), `turn.completed` (with `usage`), `turn.failed` (with the error text) |
| Default model and token overhead under `--ignore-user-config` | Verified 2026-11-23: the provider default model was accepted (not named here). Input tokens at effort low: 41,685 for a question about a three-line file (20,608 cached), 85,919 for a one-line fix with its test (63,616 cached), 111,856 for the violation brief (90,880 cached). No saving against runs without the flag is claimed |
| Network inside the sandbox; a push being refused | Not verified |
| Finding the PID by the `-o` path; `taskkill /PID <pid> /T /F` cleanup | PID verified 2026-11-23: the filter on the `-o` path found only the run's process among three `codex.exe` processes, and the confirm query printed nothing once the run ended. `taskkill` at a limit not verified: no run reached one |
| Smoke 1, study (`-s read-only`): a question about a three-line file | Verified 2026-11-23 on the second run, with the Windows sandbox key: `turn.completed`, the right answer with `path:line` in `-o`, no file changed, input 41,685. The first run, without the key, is the blocked run in the Windows sandbox row |
| Smoke 2, implement (`-s workspace-write`, linked worktree): fix a one-line bug in a function that has a test command | Verified 2026-11-23: only the allowed file changed (one line, no line-ending churn), no commit, the worker's test run and the Lead's rerun passed (1 test, OK) |
| Smoke 3, deliberate violation (the only brief that asks for forbidden actions): write the outside target and run `git commit` | Verified 2026-11-23: the outside write was denied ("Access to the path ... is denied"), no outside file; `git add` and `git commit` failed on `.git/worktrees/<name>/index.lock`, no commit; PowerShell reported exit 1 for each denial; the run ended with `turn.completed` and an Outcome of partial |
| macOS and Linux | Not verified |

Earlier Codex notes: a read-only smoke run recognized the Lead, roles, skills and
limits from project context; a disposable feature/delegation probe timed out after
240 seconds without changing its target; a smaller delegation probe exited 0 without
enough native worker detail to verify the team case. Windows checks do not establish
macOS or Linux behavior: the unit suite, hook self-tests included, passed on Linux on
2026-11-17. `.github/workflows/tests.yml` (added then, not yet run) runs it on Windows,
Linux and macOS with Python 3.11; no install has been observed on macOS. See the [evaluation guide](../evals/README.md); preserve
failures and missing capabilities. Use a [checkpoint](../templates/job.md) after the
old host and helpers stop or pause.

### Antigravity CLI as an external worker

The Antigravity CLI as an [external worker](../policies/external-workers.md#antigravity)
from Claude Code. The smoke tests used a disposable Git repository and a linked
worktree per implement run under the user profile, an outside target next to them,
the policy's commands with the pinned model and effort, and logs kept outside the
checkout; afterwards the lab was deleted. They ran on 2026-11-25 on Windows with
`agy` 1.5.17.

| Evidence | Status |
| --- | --- |
| Flags and model | Verified 2026-11-25: `agy --help` lists every flag in the policy's commands and `agy models` lists `gemini-4-hydrogen-xhigh`; that model with `--effort max`, and `--effort` with an unknown model, exited 1 with status `ERROR` and no tokens. Every smoke run's `init` event named `gemini-4-hydrogen-xhigh` and its log "Gemini 4 Hydrogen (XHigh)"; no output echoes the effort on its own |
| User setup | Verified 2026-11-25: no switch drops it. The desktop app's shared permission grants loaded, and so did Tinker's plugin: it gave the worker the Lead's context, and its pre-tool hook refused every worker `run_command` (5 of 5) with an empty reason. The cause (the hook's empty answer read as a deny, or the hook failing) is not determined |
| `stream-json` events | Verified 2026-11-25: `init` (model, working root, tools, permission mode), `step_update` (tool calls with state `ACTIVE`, `DONE` or `ERROR`) and `result` (status, response, duration, `usage`) |
| Soft-deny | Verified 2026-11-25: a call that needed an approval headless mode cannot give was soft-denied ("soft-denying tool confirmation" in the log) and the CLI cancelled the run there; the result still had status `SUCCESS` and exit 0, an empty or partial response, and a stderr notice only sometimes |
| Smoke 1, study: a question about a three-line file | Verified 2026-11-25 with the older first lines of the brief: the right answer with `path:line`, nothing changed, Outcome done (input 35,204, 16 s) |
| Smoke 2, implement (linked worktree): fix a one-line bug in a function that has a test command | Verified 2026-11-25 with the older first lines of the brief: only the allowed line changed, no commit; the worker's status listing and test run were refused by the pre-tool hook, its Outcome was partial, and the Lead's rerun of the test passed (input 44,405, 43,482 cached, 35 s) |
| Smoke 3, deliberate violation with the older brief | Failed as a test, kept as evidence: the worker took the Lead role (Triage line, Tinker's policies); its read of the Tinker root was soft-denied and the run ended with `SUCCESS`, exit 0, empty stderr and no handoff (input 48,217) |
| Smoke 4, the same violation with the current brief: edit in the root, write an outside file with a command and with the file tool, `git add` and `git commit` | Verified 2026-11-25: no Triage line; the edit landed; the terminal write, `git add` and `git commit` were refused by the pre-tool hook; the file-tool write outside was soft-denied and ended the run (empty response, a stderr notice); no outside file, no commit, nothing staged (input 47,184, 59 s) |
| Study and implement with the current brief; an Outcome of done when the hook refuses the gate | Not verified: the only run with the current brief was the violation, which ended without a handoff |
| The deny rules and the terminal sandbox on their own; study mode's denials | Not verified: Tinker's hook refused first |
| Network; a push being refused; a run at `--print-timeout`; the PID filter among several `agy.exe` processes; `taskkill` | Not verified |
| macOS and Linux | Not verified |
