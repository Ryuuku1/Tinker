# Tinker

Your software team inside **Codex, Claude Code or Antigravity**. Give the Lead an
outcome and a product repository; it coordinates the relevant specialists, does the
authorized work and returns artifacts and evidence. Nothing runs outside your AI app:
no daemon, server or launcher. Tinker works on any number of unrelated projects; it
keeps no list of them, and each project carries its own facts.

- [Set up](#set-up) - prerequisites, install, first project, optional extras
- [Use it](#use-it) - requests, the `/tinker` front door, the team
- [How a task runs](#how-a-task-runs) - playbooks, task start, retros and learning
- [Reference](#reference) - graphs, install details, platforms, hosts, validation

## Set up

### 1. Prerequisites

| Need | For | Check |
| --- | --- | --- |
| Git | everything | `git --version` |
| Python 3.11+ | installer, hooks, helper scripts, tests | `python --version` (or use [uv](https://docs.astral.sh/uv/): `uv run --no-project --python 3.12 python ...`) |
| At least one host, signed in | running the team | `claude --version`, `codex --version`, or the Antigravity app |
| [Graphify](https://github.com/Graphify-Labs/graphify#install) (optional) | code graphs for big repositories | `uv tool install graphifyy`, then `graphify --version` |
| Node.js 18+ (optional) | browser live passes in Claude Code | `node --version` |
| bash (optional) | live evals; on Windows, Git Bash | `bash --version` |

On Windows, if `python` opens the Microsoft Store, the store alias is shadowing a real
install: install Python (or use `uv`) and turn the alias off under Settings, Apps,
Advanced app settings, App execution aliases.

### 2. Get Tinker

Clone it once to a stable folder outside your projects; the installed hooks and your
local notes point at this path, so pick one you will keep.

```bash
git clone https://github.com/andrereis26/Tinker.git ~/dev/Tinker
cd ~/dev/Tinker
python -m unittest discover -s tests
```

The tests take a few minutes and should end with `OK` (some are skipped on purpose,
for example where Windows cannot create a symlink). If you use the optional Buzz kit,
also tell this checkout your platform once: `python scripts/tinker_platform.py set
windows` or `set linux` (see [Windows or Linux](#windows-or-linux)).

### 3. Choose how to run it

**A. Project mode (no install).** Open this checkout as the project in your host and
give it access to the product folder:

| Host | Start |
| --- | --- |
| Claude Code | `claude --plugin-dir . --add-dir <absolute-product-path>` from this checkout |
| Codex CLI | `codex --add-dir <absolute-product-path>` from this checkout |
| Codex app | Add/open this folder as a project, then grant the product folder |
| Antigravity | Open this folder as a project; grant product access through its controls |

Trust the project when the host asks, or it will not load local configuration. In
Claude Code, chats opened here also get Tinker's [project settings](#claude-code-extras).

**B. Installed in the apps (recommended for daily use).** Every chat, in any project,
starts with the Lead, this checkout's notes and open checkpoints, and an approval gate
for risky commands. Run the installer yourself in a terminal (the gate refuses it from
inside an agent):

```bash
python scripts/install_apps.py --dry-run     # shows what it will write and register
python scripts/install_apps.py               # or: --app claude|codex|antigravity
```

Then restart the apps. In Codex, trust the hooks in `/hooks` after every install. In
Claude Code the front door is `/tinker:tinker` and the teammates are `tinker:<role>`.
The installer refuses an app where another Tinker installation is already enabled,
for example an organization's edition with the same plugin id; use project mode on
that machine instead. Uninstall with `python scripts/install_apps.py --uninstall`.
Details: [install reference](#install-reference).

### 4. Check it works

Ask a chat for `tinker help`, then `tinker status` (in Claude Code the skill is
namespaced: `/tinker:tinker help`). Help lists the front-door forms; status shows each
app's install state, open checkpoints, recent retros and the eval baseline. If a host does not show Tinker's skills or agents,
see [provider setup and verification limits](docs/providers.md).

### 5. Give each project a playbook

In a chat, ask:

```text
tinker playbook <absolute-product-path>
```

Tinker drafts a `## Agent playbook` section for that project's own `AGENTS.md` from its
README, scripts, CI files and Git history: base branch, gate commands, commit style,
worktrees, a live-pass recipe, `Graph: auto|on-demand` and pitfalls
([template](templates/agent-playbook.md)). It shows the change and writes it only when
you approve. Projects without one still work; Tinker infers the facts each time and
says so. Do this once per project, and let `/tinker learn` refine it over time.

### 6. Optional extras

#### Claude Code extras

- **Destructive-Git guard.** Chats opened in this checkout load `.claude/settings.json`,
  which denies force pushes, `reset --hard`, `clean`, `restore`, forced branch and
  worktree deletion and similar, and asks before deleting a remote branch. Installed
  mode gets the equivalent from the approval gate.
- **Browser live passes.** Install the official Playwright plugin once:
  `claude plugin install playwright@claude-plugins-official`. Chats opened here are
  already configured for it (isolated profile, `localhost` and `127.0.0.1` only).
  For chats opened in other folders, copy the `env` block from
  [providers](docs/providers.md#claude-code) into `~/.claude/settings.json`. A UI change
  then gets a live pass you can watch when its playbook has a `Live pass` recipe.

#### Routines

Ask `tinker schedule defaults` to set up, in your host's own scheduler, the weekly
maintenance (retros review, stale notes, up to three proposed improvements), the
monthly upgrade scan and a daily graph refresh for projects with `Graph: auto`
([routines](templates/routines.md)). They run unattended, so they only report.

#### First live eval baseline (needed for `/tinker learn`)

`learn` keeps an edit only when the live evaluation gate passes, and the gate needs a
baseline. Record it yourself once, on the machine and Claude account you use for
Tinker (each run is a real Claude session and uses your plan):

```bash
python scripts/eval_live.py run                        # 15 cases, one run each
python scripts/eval_live.py gate --result evals/live/results/<runId>.json --accept
git add evals/live/accepted.json && git commit -m "chore(evals): accept the first live baseline"
```

Read the failing graders before accepting: the first run is also where case wording
gets tuned. See the [evaluation guide](evals/README.md#live-evals-claude-code).

### 7. Keep it up to date

```bash
git pull
python -m unittest discover -s tests
python scripts/install_apps.py               # installed mode only; then restart the apps
```

`team status` shows any app still running an older copy. Your local state under
`.tinker/` (notes, checkpoints, retros, graphs, eval results) is git-ignored and
survives pulls.

## Use it

Send ordinary requests, naming the product repository:

```text
Team, implement customer invitations in <absolute-product-path>.
Work through design, implementation, testing and review. Preserve my existing edits.

Grill me on this plan for <absolute-product-path> before we build anything: ...

Investigate why the export job times out in <absolute-product-path>; fix it.

Review my staged changes in <absolute-product-path>.

Designer, propose a clearer onboarding flow for <absolute-product-path>. Design only.
```

For a new product, give its destination folder and acceptance criteria. No slash
command, ticket id or role name is required; you may address any specialist by role.

### The `/tinker` front door

Shortcuts, not required syntax. In Claude Code type `/tinker:tinker <form>`; in other
hosts, invoke the `tinker` skill or just say the form ("tinker status").

| Form | Does |
| --- | --- |
| `/tinker <task>` | Routes the task to the right workflow in this chat |
| `/tinker status` | Install state, open checkpoints, recent retros, the eval baseline, the latest maintenance report |
| `/tinker playbook <repo>` | Drafts that repository's `## Agent playbook` section for your approval |
| `/tinker learn [focus]` | Turns recent retros into at most three gated edits on a `tinker/learn-<date>` branch |
| `/tinker eval [args]` | Runs the live eval cases and the gate (asks first before more than 20 runs) |
| `/tinker schedule <what> <when>` | Creates a routine in the host's scheduler; `schedule defaults` offers the standard ones |
| `/tinker help` | Lists these forms |

### Your team

| Role | Responsibility |
| --- | --- |
| [Lead](AGENTS.md) | Own the outcome, coordinate and integrate |
| [Product Manager](roles/product-manager.md) | Needs, scope and acceptance |
| [Designer](roles/designer.md) | User flows, interactions and visual direction |
| [Engineer](roles/engineer.md) | Implementation and defect investigation |
| [Test Engineer](roles/test-engineer.md) | Meaningful tests and verification |
| [Reviewer](roles/reviewer.md) | Independent assessment of actual changes |
| [Researcher](roles/researcher.md) | Evidence-backed technical answers |
| [Technical Writer](roles/technical-writer.md) | Usable product documentation |
| [Delivery Engineer](roles/delivery-engineer.md) | Release preparation and authorized delivery |
| [Explorer](roles/explorer.md) | Cheap read-only search: files, symbols, callers, conventions |

Roles are persistent instructions; real workers are native host agents, used only
when useful: at most two active helpers, one writer including the Lead, no recursive
delegation. Small jobs stay with the Lead. Unavailable helpers mean transparent Lead
work; role switching is never presented as independent review. The Explorer is the
one cost-tiered helper: in Claude Code it runs on the small model with only its own
charter; everything else uses your session's model.

### Workflows

Seven workflows sit behind the front door: **shape** (briefs, user flows and
acceptance criteria, plus a grill mode that settles a plan one decision at a time and
looks up what the code already answers), **implement**, **investigate**, **review**,
**artifacts** (user stories, documentation, diagrams, ADRs and release notes, saved as
Markdown first, GitHub issues or a project board only on approval), **Graphify** and
**team** (status, schedules, approvals, lesson reviews). Implementation and review
follow a minimalism ladder: does the code need to exist, does the codebase or the
standard library already cover it, and never trim validation or error handling to
save lines. Research, testing and delivery use their charters directly. Running UI,
API or CLI changes are checked per [application verification](policies/app-verification.md).
Optional [domain packs](templates/domain-pack.md) load only when you name one or the
repository's instructions link it.

## How a task runs

1. **Target.** The Lead uses the repository you name or the current product
   workspace, never a guess, and reads its own instructions and `## Agent playbook`.
2. **Task start.** It fetches only the base branch and starts new work from
   `origin/<base>`. A branch it continues is rebased only when it is clean and none of
   its commits is pushed; otherwise it reports how far behind it is. It never stashes,
   resets or force-pushes your work ([task start](policies/workspace.md#task-start)).
   With `Graph: auto`, the graph refreshes in the background.
3. **Work and verify.** The workflow runs the playbook's gates, narrowest first, and
   reports failed, skipped and unavailable checks exactly
   ([evidence policy](policies/evidence.md)). Noisy test output can go through
   `python scripts/filter_test_log.py`, which keeps failures and totals and says what
   it dropped. Substantial or delegated work keeps a checkpoint in `.tinker/tasks/`.
4. **Deliver.** Changes are left as the playbook says. Commits, pushes, publishing
   and remote changes happen only when you ask.
5. **Retro.** The final message ends with a short retro, also saved to the ignored
   `.tinker/retros/`. It may propose one small edit; nothing is applied then.
6. **Learn.** `/tinker learn` reads recent retros, applies at most three edits to
   Tinker on a `tinker/learn-<date>` branch, runs the live eval gate and commits only
   if it passes. Facts about a project become a proposed bullet in its playbook
   instead. You review and merge; nothing is pushed
   ([learning policy](policies/learning.md)).

## Reference

### On-demand Graphify graphs

Graphify runs for an explicit graph request, a broad topology question that source
inspection cannot settle, or task start in a project whose playbook says
`Graph: auto`. Graphs live under this checkout's ignored `.tinker/graphs/`, a baseline
plus one per registered linked worktree; product repositories receive no graph output.

The primary checkout must be clean and on the baseline branch you pass with
`--baseline-branch` (no repository has a built-in default). The helper does not fetch.
It refreshes the baseline before indexing a selected worktree's clean committed
`HEAD`, selected by absolute path or by a ticket matching exactly one registered path
or branch. Dirty worktrees are unavailable until committed. Extraction reads a
temporary detached checkout of each commit, so ignored or hidden local files never
enter a graph.

```text
python scripts/graphify_project.py <absolute-primary-path> --baseline-branch <branch>
python scripts/graphify_project.py <absolute-primary-path> --worktree-path <absolute-worktree-path> --baseline-branch <branch>
python scripts/graphify_project.py <absolute-primary-path> --action status --worktree-path <absolute-worktree-path>
python scripts/graphify_project.py <absolute-primary-path> --action query --worktree-path <absolute-worktree-path> --query "<topology question>" --budget 1200
python scripts/graphify_project.py <absolute-primary-path> --action cleanup --worktree-path <absolute-worktree-path>
```

`status` returns graph and HTML paths only when the worktree graph matches its clean
`HEAD` and recorded baseline commit; queries never fall back to an older graph.
Cleanup removes only that worktree's transient `cache/`. If Graphify is missing or
extraction fails, the Lead continues from source files and reports the graph status.
Including documents or media may need a model backend; discuss its data path first.

### Install reference

The installer renders a small bundle under `~/.tinker/`, stages and self-tests it, and
registers it with `claude`, `codex` and as an Antigravity plugin. It replaces or
deletes only files it recorded with their hash, restores the previous files if an
update fails, and reports each app separately: one app can be current while another
is stale or waiting for a recovery command. Force pushes, protected-branch pushes,
branch deletion, discarding work, recursive deletes, remote changes, publishing and
credential changes need your approval; scheduled runs cannot approve anything. See
[per-app details and limits](docs/providers.md#optional-user-level-install).

### Windows or Linux

Tinker's own scripts are Python and run on both. The optional [Buzz kit](integrations/buzz/kit/GUIDE.md)
has a PowerShell 7 version for Windows and a bash version for Linux, kept in step by
tests. The choice lives in the ignored `.tinker/platform.json`:

```text
python scripts/tinker_platform.py                 # show the platform in use (auto-detected until you set one)
python scripts/tinker_platform.py set linux       # or windows, or auto
python scripts/install_apps.py --platform linux   # the same, while installing into the apps
python scripts/tinker_platform.py kit setup --owner-npub <npub> --repository <path>   # that platform's kit script
```

`kit` takes the bash spelling of the options on both platforms and turns it into
PowerShell parameters on Windows. `TINKER_PLATFORM=windows|linux` overrides the stored
choice for one command.

### Continue or switch hosts

Substantial or delegated work gets a checkpoint at `.tinker/tasks/<UUID>.md` in this
checkout; the Lead gives you its path. Ask "Prepare this job for handoff and stop its
helpers", stop the old session, then in the other host say:

```text
Continue the job from <absolute-checkpoint-path>. Recheck the repository state first.
```

The next host resumes from evidence, not the other provider's conversation. Never
run two hosts on the same job at once. Notes live as source-backed Markdown under the
ignored `.tinker/knowledge/`; checkpoints and notes never enter product repositories.

### What is where

| Path | Holds |
| --- | --- |
| `AGENTS.md` | The Lead charter, loaded in every session |
| `.agents/skills/` | The front door and the seven workflows |
| `roles/` | Specialist charters; their front matter generates the native agents |
| `policies/` | Evidence, safety, workspace (task start), delegation, tools, knowledge, learning, app verification |
| `templates/` | Agent playbook, checkpoint, ADR, user story, routines, domain pack, recipes |
| `scripts/` | Installer, hook runtime, Graphify helper, live eval runner, test-log filter, platform helper |
| `evals/` | Offline case catalog and grader; live Claude cases under `evals/live/` |
| `.claude/`, `.codex/`, `.agents/agents/`, `.gemini/` | Generated native descriptors and Claude project settings |
| `.tinker/` (ignored) | Your local state: checkpoints, retros, notes, graphs, reports, evidence |

### Boundaries and validation

Local work proceeds within your request. Commits, pushes, publishing, deployment,
external messages and destructive actions need explicit authorization. Native
permissions enforce access; instructions alone are not a sandbox, and the installed
gate classifies command text, so it guards against mistakes rather than sandboxing.

Run `python -m unittest discover -s tests` for package, installer, grader and runner
checks, and `claude plugin validate --json .` for the Claude manifest (warnings about
the missing author and the root `CLAUDE.md` are expected). These prove structure, not
agent behavior. The [evaluation guide](evals/README.md) covers the offline cases for
all hosts and the live Claude cases; a configured host is not automatically verified.
See [architecture](docs/architecture.md), [design history](docs/history.md) and
[extension guidance](docs/extending.md). Original Gemini CLI files remain as
secondary compatibility; they do not constitute Antigravity support.
