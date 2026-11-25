# Tinker

Tinker is a software team that lives inside the AI coding app you already use:
**Claude Code, Codex or Antigravity**. Tell the Lead the outcome you want and which
repository it is for. It sizes the job, brings in only the specialists it needs
(product, design, engineering, testing, review, research, writing, delivery), does
the work you authorized, and hands back the result with its evidence: the gates it
ran, what failed or was skipped, and what is still open. Nothing runs outside your
app: no daemon, server or launcher. Tinker works on any number of unrelated projects;
it keeps no list of them, and each project carries its own facts.

| You ask for | You get back |
| --- | --- |
| A feature, refactor or any other edit, however small | The change in the project's own style, verified by its own gates |
| A bug, failure or flaky test | The root cause with evidence, the fix, and regression coverage (ideally a test that failed before the fix) |
| A review of a diff, branch or PR | Findings with `path:line`; nothing changes |
| A rough idea, or a plan to test | A brief with user flows and acceptance criteria, or a grilling that settles the plan one decision at a time |
| Stories, docs, diagrams, ADRs, release notes | Markdown first; GitHub issues or a project board only on approval |
| A question about the code | The answer, with `path:line` evidence |

## Why Tinker

- **One team, any host.** One charter, one set of roles and policies, installed
  natively into each app. A job checkpointed in one host continues in another from
  evidence, not from the other app's conversation.
- **Evidence, not optimism.** Every task runs the project's own gates, narrowest
  first, and reports failed, skipped and unavailable checks exactly. A running UI,
  API or CLI change is also checked in the running app when its playbook says how.
- **Right-sized.** The Lead keeps small jobs to itself and fans out only when helpers
  pay for themselves. In Claude Code the Explorer searches on the small model, noisy
  test output arrives trimmed to failures and totals, and `usage_report.py` shows
  tokens and cost per workflow.
- **Your work stays safe.** New work starts from the fresh base branch without
  stashing, resetting or force-pushing your edits. Commits, pushes, publishing and
  remote changes wait for your word, the installed gate asks before risky commands,
  and product repositories never receive Tinker's files.
- **It learns, under test.** Every task ends with a retro. `/tinker learn` turns
  recent retros into at most three edits on a branch and commits them only when the
  live eval gate (real Claude Code sessions, a regression and a held-out set, graded
  by a pinned judge) shows no lower score and no higher cost. You review and merge.
- **It keeps itself current.** A daily check with no agent and no tokens tells a new
  chat when Tinker is behind, and `update.py` pulls and reinstalls.

## Contents

- [Set up](#set-up) - prerequisites, install, first project, optional extras
- [Use it](#use-it) - requests, the `/tinker` front door, the team
- [How a task runs](#how-a-task-runs) - playbooks, task start, retros and learning
- [Reference](#reference) - graphs, install details, platforms, hosts, validation

## Set up

### 1. Prerequisites

| Need | For | Check |
| --- | --- | --- |
| Git | everything | `git --version` |
| Python 3.11+ | installer, hooks, helper scripts, tests | `python --version`, `python3` on macOS and Linux (or use [uv](https://docs.astral.sh/uv/): `uv run --no-project --python 3.12 python ...`) |
| At least one host, signed in | running the team | `claude --version`, `codex --version`, or the Antigravity app |
| [Graphify](https://github.com/Graphify-Labs/graphify#install) (optional) | code graphs for big repositories | `uv tool install graphifyy`, then `graphify --version` |
| Node.js 18+ (optional) | browser live passes in Claude Code | `node --version` |
| bash (optional) | live evals; on Windows, Git Bash | `bash --version` |

On Windows, if `python` opens the Microsoft Store, the store alias is shadowing a real
install: install Python (or use `uv`) and turn the alias off under Settings, Apps,
Advanced app settings, App execution aliases.

On macOS and Linux, type `python3` wherever this guide says `python`. The `python3`
that comes with macOS is often 3.9, which the installer refuses: install 3.11 or newer
from python.org, Homebrew (`brew install python`) or `uv`, and run the installer with
it. The hooks keep running the interpreter that installed them.

### 2. Get Tinker

Clone it once to a stable folder outside your projects; the installed hooks and your
local notes point at this path, so pick one you will keep.

```bash
git clone https://github.com/Ryuuku1/Tinker.git ~/dev/Tinker
cd ~/dev/Tinker
python -m unittest discover -s tests
```

The tests take a few minutes and should end with `OK` (some are skipped on purpose,
for example where Windows cannot create a symlink).

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
Uninstall with `python scripts/install_apps.py --uninstall`.

Where another Tinker installation already owns `~/.tinker` or is enabled (for example
an organization's edition with the same plugin id), install beside it under a name of
your own, and pass the same name to every later install, `--uninstall` and `status`:

```bash
python scripts/install_apps.py --instance personal --dry-run
python scripts/install_apps.py --instance personal   # ~/.tinker-personal, tinker@tinker-personal
```

Claude Code then gets this one installed but turned off, so a chat never runs both;
the installer prints how to switch, for every project or just one. Codex and
Antigravity are left out while the other one is enabled there. Project mode works on
such a machine too.
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
  worktree deletion and similar. It has no ask rules, so bypass mode never stops for
  an approval. Installed mode gets the equivalent from the approval gate.
- **Browser live passes.** Install the official Playwright plugin once:
  `claude plugin install playwright@claude-plugins-official`. Chats opened here are
  already configured for it (isolated profile, `localhost` and `127.0.0.1` only).
  For chats opened in other folders, copy the `env` block from
  [providers](docs/providers.md#claude-code) into `~/.claude/settings.json`. A UI change
  then gets a live pass you can watch when its playbook has a `Live pass` recipe.

#### Design and engineering skills

UI work loads third-party design skills ([frontend design](policies/frontend-design.md)):
Impeccable for every UI edit, Emil Kowalski's motion and polish skills, Taste for sites
with no design system, and UI UX Pro Max as a lookup. Code work loads three pinned
engineering skills (below). They are not part of this repository; install them at user
level, for every project, with Node.js 18+ (re-run after a pin changes):

```bash
python scripts/install_apps.py --skills --dry-run   # shows the npx commands
python scripts/install_apps.py --skills             # or: --app claude|codex|antigravity
```

It runs the pinned `skills` and `impeccable` CLIs with telemetry off and without
Impeccable's design hook (enable that per project with `/impeccable hooks on`). Emil
Kowalski's skills, Taste, UI UX Pro Max and the engineering skills come from their
upstream repositories at full commits, and Impeccable from its pinned CLI, which
downloads Impeccable's current skill. `--design-skills` still works as an alias.
`skills-lock.json` records the reviewed
versions. Taste 2.5.1 brings its own Stop hook. Claude Code adds it once that skill
is invoked, and it holds a turn only while a Taste build is armed. The [design skills study](docs/design-skills.md) explains why each
source was chosen and how to bump or roll back a pin. Unlike the Tinker install, this
works next to another Tinker installation.

#### Engineering skills

Code changes, defects and reviews use superpowers, ponytail and three pinned skills
(addyosmani's `security-and-hardening` and `deprecation-and-migration`, Trail of Bits'
`sharp-edges`) at named steps ([engineering skills](policies/engineering-skills.md)):
test first, root cause before a fix, fresh evidence before "done", and security,
removal and misuse checks on backend changes. Each has a fallback, so a host without
them applies the rule by hand. The [engineering skills study](docs/engineering-skills.md)
lists the reviewed versions and how to install the two plugins.

#### Routines

Ask `tinker schedule <what> <when>` to create, in your host's own scheduler, a role's
run on a repository or a daily graph refresh for projects with `Graph: auto`
([routines](templates/routines.md)). They run unattended, so they only report.

#### First live eval baseline (needed for `/tinker learn`)

`learn` keeps an edit only when the live evaluation gate passes, and the gate needs a
baseline. Record it yourself once, on the machine and Claude account you use for
Tinker (each run is a real Claude session and uses your plan):

```bash
python scripts/eval_live.py run --adaptive             # every case once, a short one twice more
python scripts/eval_live.py gate --result evals/live/results/<runId>.json --accept
git add evals/live/accepted.json && git commit -m "chore(evals): accept the first live baseline"
```

Read the failing graders before accepting: the first run is also where case wording
gets tuned. See the [evaluation guide](evals/README.md#live-evals-claude-code).

### 7. Keep it up to date

```bash
python scripts/update.py --dry-run   # fetches, then says what it would pull and reinstall
python scripts/update.py             # fast-forwards and reinstalls; then restart the apps
```

`update.py` fast-forwards the default branch only when this checkout is on it, clean and
without commits of its own (otherwise it says why and changes nothing), then re-runs
the installer for each installation made from this checkout that is stale, with the
apps, interpreter and `--instance` it recorded. Run it yourself: like the installer,
the gate refuses it inside an agent, except `--check` and `--dry-run`. Each run records
its result in `.tinker/update.json`, which `/tinker status` and the session-start note
read.

The installer also schedules `update.py --check` once a day at 09:00, caught up after
sleep or shutdown: a `git fetch` with no agent and no tokens, so a new chat says when
Tinker is behind. That uses Windows Task Scheduler (`--update-check-hours 1-23` checks
more often, `0` removes it); on macOS and Linux the installer prints the crontab line
to add instead. `python scripts/update.py --schedule` and `--unschedule` manage it
directly and never touch a task that runs another checkout's script.

`/tinker status` shows any app still running an older copy. Your local state under
`.tinker/` (notes, checkpoints, retros, graphs, eval results) is git-ignored and
survives pulls.

```bash
python scripts/reload.py --dry-run [path ...]   # what a cleanup would remove; drop --dry-run to do it
python scripts/usage_report.py --days 7         # tokens and estimated cost per workflow, and the cache lines
```

`reload.py` fetches, removes only worktrees and branches proven merged (an ancestor of
the default branch, every commit already upstream, or the head of a merged pull
request), keeps anything dirty, locked or in use, and fast-forwards the default branch.
The installed gate asks before it runs without `--dry-run`, except in Claude Code's
bypass mode. `usage_report.py` reads
Claude Code and Codex session logs; Claude rows are priced at list prices, Codex rows
show tokens only, and Antigravity is not measured. Below the table, a few cache lines count
only requests made in the window: the share read from the prompt cache, the cost split,
rebuilds after it expired, compactions, a new chat's first request per folder and the
helpers' share; `--cache-detail` adds the rest.

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
| `/tinker <task>` | Routes the task to the right workflow in this chat; a question gets a direct answer with `path:line` evidence |
| `/tinker` | Where you stand: branch, changed files, open checkpoints and up to three next steps |
| `/tinker status` | Health (checkout behind its remote at the last update check, stale installs), install state, open checkpoints, recent retros, the eval baseline, the newest report, cost per workflow |
| `/tinker update` | Checks whether this checkout is behind its remote and gives you the command that pulls and reinstalls |
| `/tinker reload [path ...]` | Pulls the default branch and removes worktrees and branches proven merged; reports what it kept |
| `/tinker remember <fact>` | Saves the fact as a knowledge candidate that every host reads |
| `/tinker playbook <repo>` | Drafts that repository's `## Agent playbook` section for your approval |
| `/tinker learn [focus]` | Turns recent retros into at most three gated edits on a `tinker/learn-<date>` branch |
| `/tinker eval [args]` | Runs the live eval cases and the gate (asks first before more than 20 runs) |
| `/tinker schedule <what> <when>` | Creates a scheduled run in the host's scheduler: a role's task on a repository, or the daily graph refresh |
| `/tinker help` | Lists these forms |

### Your team

| Role | Responsibility |
| --- | --- |
| [Lead](AGENTS.md) | Own the outcome, coordinate and integrate |
| [Engineer](roles/engineer.md) | Implementation and defect investigation |
| [Reviewer](roles/reviewer.md) | Independent assessment of actual changes |
| [Researcher](roles/researcher.md) | Evidence-backed technical answers |
| [Explorer](roles/explorer.md) | Cheap read-only search: files, symbols, callers, conventions |

Product, design, writing, testing and delivery expertise lives in the workflows,
which the Lead runs itself. Roles are persistent instructions; real workers are
native host agents, used only when useful: the Lead sizes the team per task for the best result per cost, with no
fixed ceiling, one writer per working tree and no recursive delegation. Small jobs
stay with the Lead. UI work also follows [frontend design](policies/frontend-design.md): a design gate
before the first edit, the design skills it picks, an anti-generic floor and screenshot evidence. Unavailable helpers mean transparent Lead
work; role switching is never presented as independent review. The Explorer is the
one cost-tiered helper: in Claude Code it runs on the small model at low effort with
only its own charter (no `CLAUDE.md`); everything else uses your session's model.

From Claude Code, the Codex CLI joins as an [external worker](policies/external-workers.md)
only when you ask in plain words, in any language: "consult Codex" for one read-only
second opinion, "use Codex too for these tasks", or "parallelize with Codex" to hand it
the eligible pieces, each edit in its own worktree. It covers only the tasks you name
("this session" means the rest of that chat); there is no command, automation or
quota trigger, and the Lead never offers it. It verifies Codex's work, reports its
tokens and does not ask again within that scope, though in Claude Code's default
permission mode the installed gate still asks once per `codex exec`. The Antigravity
CLI joins the same way on "consult Antigravity", "use Antigravity too for these
tasks" or "parallelize with Antigravity" (or Gemini), pinned for now to Gemini 4
Hydrogen at xhigh; the installed gate asks once per `agy -p` run the same way.

### Workflows

Six workflows sit behind the front door: **shape** (briefs, user flows and
acceptance criteria, plus a grill mode that settles a plan one decision at a time and
looks up what the code already answers), **implement**, **investigate**, **review**,
**artifacts** (user stories, documentation, diagrams, ADRs and release notes, saved as
Markdown first, GitHub issues or a project board only on approval) and **Graphify**;
the front door itself covers status, schedules and lesson reviews. Implementation and review
follow a minimalism ladder: does the code need to exist, does the codebase or the
standard library already cover it, and never trim validation or error handling to
save lines. Research uses the Researcher charter; testing and delivery stay with the Lead. Running UI,
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
   it dropped. In Claude with the installed hooks, a test, build or lint output over
   200 lines arrives trimmed that way, with the full log saved in the temp folder. Substantial or delegated work keeps a checkpoint in `.tinker/tasks/`.
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
Cleanup removes only that worktree's transient `cache/`. Each graph records the
Graphify release that built it; after an upgrade the baseline is extracted from scratch
and worktree graphs reseed from it, because node ids change between releases. A graph
too large for Graphify's interactive view gets a placeholder `graph.html` and still
answers queries. If Graphify is missing or extraction fails, the Lead continues from
source files and reports the graph status.
Including documents or media may need a model backend; discuss its data path first.

### Install reference

The installer renders a small bundle under `~/.tinker/` (`~/.tinker-<name>/` with
`--instance <name>`), stages and self-tests it, and
registers it with `claude`, `codex` and as an Antigravity plugin. It replaces or
deletes only files it recorded with their hash, restores the previous files if an
update fails, and reports each app separately: one app can be current while another
is stale or waiting for a recovery command. Force pushes, protected-branch pushes,
branch deletion, discarding work, recursive deletes, remote changes, publishing and
credential changes need your approval; scheduled runs cannot approve anything. In
Claude Code's bypass and auto modes it asks nothing: you chose no prompts (auto leaves
each call to Claude Code's own classifier), so it denies only tampering with Tinker's
state and unattended runs. It also
schedules the daily update check of [section 7](#7-keep-it-up-to-date). See
[per-app details and limits](docs/providers.md#optional-user-level-install).

### Continue or switch hosts

Substantial or delegated work gets a checkpoint at `.tinker/tasks/<UUID>.md` in this
checkout; the Lead gives you its path. A change across several separately tested areas
is planned there as slices, run and verified one at a time; after a green slice in a
long chat, the Lead offers to continue in a fresh one from the checkpoint. Ask "Prepare
this job for handoff and stop its helpers", stop the old session, then in the other
host say:

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
| `.agents/skills/` | The front door and the six workflows |
| `roles/` | Specialist charters; their front matter generates the native agents |
| `policies/` | Evidence, safety, workspace (task start), delegation, external workers, tools, knowledge, retro, learning, app verification |
| `templates/` | Agent playbook, checkpoint, worker brief, ADR, user story, routines, domain pack, recipes |
| `scripts/` | Installer, hook runtime, self-update, Graphify helper, live eval runner, test-log filter, merged-branch cleanup, usage report |
| `evals/` | Live Claude cases under `evals/live/` and the [evaluation guide](evals/README.md) |
| `.claude/`, `.codex/`, `.agents/agents/` | Generated native descriptors and Claude project settings; `.gemini/agents/` holds the hand-kept Antigravity reviewer |
| `.tinker/` (ignored) | Your local state: checkpoints, retros, notes, graphs, reports, evidence |

### Boundaries and validation

Local work proceeds within your request. Commits, pushes, publishing, deployment,
external messages and destructive actions need explicit authorization. Native
permissions enforce access; instructions alone are not a sandbox, and the installed
gate classifies command text, so it guards against mistakes rather than sandboxing.

Run `python -m unittest discover -s tests` for package, installer, gate and runner
checks, and `claude plugin validate --json .` for the Claude manifest (warnings about
the missing author and the root `CLAUDE.md` are expected). These prove structure, not
agent behavior. The [evaluation guide](evals/README.md) covers the live Claude cases;
a configured host is not automatically verified.
See [architecture](docs/architecture.md), [design history](docs/history.md) and
[extension guidance](docs/extending.md). Original Gemini CLI files remain as
secondary compatibility; they do not constitute Antigravity support.
