# Design history

Background for the [architecture](architecture.md). These records explain how the
current design was reached; they are not instructions, and the architecture document
governs where they differ.

The [2026-10-01 workflow improvements](reference-sync-2026-10-01.md) record generic
guidance changes, verification and scope boundaries.

## 2026-09-26: renamed to Tinker

The project formerly named Tinker Bot is now Tinker, and its history was rewritten
into technical commits. Revisions cited below, such as `1bd44c0`, belong to the
pre-rename history, which is kept under the local tag `archive/tinker-bot`.

| Former | Now |
| --- | --- |
| Plugin `tinker-bot@tinker-bot-local` | `tinker@tinker-local` |
| Skills `tinker-bot-<name>` | `tinker-<name>` |
| User state `~/.tinker-bot/`; checkout state `.tinker-bot/` | `~/.tinker/`; `.tinker/` |
| Runtime `scripts/tinker_bot.py` | `scripts/tinker_runtime.py`. The tamper guard matches the runtime's name anywhere in a command, and a bare `tinker` would match every path inside a Tinker checkout |

The name is shared with the original PowerShell Tinker analyzed below and with an
organization's edition, which can be installed under the same plugin id and home
folder. The installer therefore decides ownership only from its own records. It
refuses an app where a Tinker plugin it did not record is enabled, and it never reads
or rewrites an `apps.json` that it did not write. Installations made under the former
name are not migrated; uninstall them with the installer at `archive/tinker-bot` first.

## 2026-09-26: a dependable generic team

The refactor strengthened the existing design instead of replacing it. It was planned
after comparing this project at pre-rename revision `1bd44c0` with an organization's
published edition of Tinker (baseline `750955d`, later `7866b0f`, which merged its
team-domains branch and a separate evaluation fix). Its application verification recipes, team
playbooks, shared retrospectives and evaluation-backed improvement informed this
change; its aggregate evaluation scores were not copied, and no improvement of equal
size is claimed. Its browser-planning evaluation showed planning behavior, not actual
browser verification.

| Area | Decision |
| --- | --- |
| Lead, specialist roles and native host execution | Preserved, with provider defaults |
| Application verification recipes | Adapted into optional, generic UI/API/CLI verification guidance |
| Team playbooks and shared retrospectives | Adapted as optional domain packs and evidence-backed learning |
| Evaluation-backed improvement | Adopted, keeping Tinker's evidence provenance and adding independent coverage checks |
| Repository registry, default product, work-tracker routing | Not imported into the generic core |
| Mandatory graph refresh, automatic retrospectives after every task | Not adopted |
| Fixed models, larger worker budgets, headless launcher | Not adopted |
| Maintenance routines | Opt-in native-scheduler prompt templates; nothing is scheduled automatically |

Defects fixed with regression tests first: approval identity that ignored edit contents
and scheduler arguments; a single-use grant that concurrent retries could all consume on
Windows (concurrent `os.replace` renames of one file all report success there);
unreadable session state and stale presence writes that could turn an unattended run
into an attended one; gated payloads missing required fields passing silently; installer
writes and a directory marker that could overwrite or delete files the installer did not
own; one app's update marking every app current; and Graphify branches chosen from two
product names.

Compatibility changes: earlier grants and pending approvals without a fingerprint are
expired; Graphify needs `--baseline-branch` to establish a baseline for every
repository, including those that relied on a built-in default; the installer keeps
`apps.json` after a full uninstall, as the ownership record of the runtime it leaves.

## Original specification review and reference analysis

Two independent read-only workers reviewed the specification and reference
repository before implementation: Systems Architect and Adversarial Reviewer.
Both recommended removing the runtime. Their source findings agreed; there was
no unresolved architectural disagreement. The architect favored optional native
reviewer adapters; the reliability reviewer stressed that those cannot guarantee
isolation under all parent settings. Keep small adapters, require effective
permission checks, and explicitly fall back when restrictions are unavailable.

The subsequent user-approved software-team plan expanded roles and native adapters,
replaced the lifetime worker ceiling with a concurrency limit, and made substantial
job handoffs portable across hosts. It preserved the instruction-first architecture.

| Original assumption | Review finding | Decision and resulting change |
| --- | --- | --- |
| Persistent teammates need a state engine | Role identity is not a process | Lead plus eight specialist charters, native sessions and shared handoffs |
| Every responsibility needs a skill | Questions, checks and learning need no separate workflow | Six focused skills, including on-demand clean-commit Graphify and team status; other responsibilities use role guidance |
| Existing CLI is a useful starting point | It records unexecuted success | No orchestration CLI or provider adapter code; focused Graphify and in-app hook helpers |
| Tool-policy JSON enforces safety | The reference only renders tool names | Native restrictions plus candid fallback; the optional PreToolUse hook is native enforcement, classified in code |
| Two-worker setting is a hard total quota | Sequential specialists need a concurrency rule | Two active helpers, one writer including Lead, no lifetime ceiling |
| Automatic memory makes agents persistent | Stale and irrelevant entries enter context | Selected scoped notes; deliberate candidate promotion; turn one lists only validated note paths |
| Cleanup and routines are core services | They add state and can remove user work | Direct workflow checks; no automatic cleanup; hooks only in the optional in-app runtime |
| Static policy tests demonstrate behavior | They only find words in instructions | Separate package checks, synthetic grader tests and observed runs |

## Reference component disposition

Reference analyzed: the original PowerShell Tinker, revision `733c0a9a96c5ec1395e38bfaee2105b780c758a5`.
REMOVE means excluded from this project, not deleted from the reference repository.

| Reference component | Disposition | Replacement |
| --- | --- | --- |
| AGENTS, CLAUDE, GEMINI | SIMPLIFY | Concise canonical agreement and relative imports |
| `config/bots/`, `tinker-bot.ps1` | REDESIGN | On-demand role charters and native workers |
| `config/skills/` | REMOVE | One physical source per workflow |
| `skills/` and references | KEEP / SIMPLIFY | Six focused workflows; common policy centralized |
| `config/routines.json`, `tinker-routine.ps1` | REPLACE WITH NATIVE CAPABILITY | Workflow steps; user-requested host scheduling, with a validated `schedule-plan` |
| `config/approvals.json`, `tinker-approval.ps1` | REPLACE WITH NATIVE CAPABILITY | Authorization boundaries, host permissions and the optional hook gate (no policy file) |
| `tinker.ps1`, root wrappers, `tinker-router.ps1` | REMOVE | Host reasoning, execution and configured models |
| `tinker-context.ps1` | REPLACE WITH NATIVE CAPABILITY | Search, focused reads and host compaction |
| `tinker-memory.ps1`, `tinker-learner.ps1` | REDESIGN | Optional knowledge notes and candidates |
| `tinker-workspace.ps1` | REPLACE WITH NATIVE CAPABILITY | Host sessions and Git worktrees |
| `tinker-graphify.ps1`, graph hooks | REPLACE | Small Python helper runs upstream Graphify on demand for a clean baseline and selected worktree; output stays in ignored `.tinker/graphs/`; other tools' graph state is never written |
| `tinker-cleanup.ps1`, report cleanup | REMOVE | Explicit scoped cleanup when needed |
| Repository registry and resolver | REMOVE | Explicit target paths; no default product |
| Installer and uninstaller | REDESIGN | Local checkout, or the opt-in user-level installer with ownership records |
| Diff and log helpers | REPLACE WITH NATIVE CAPABILITY | Git/test-runner filters, preserving failure summaries |
| Product-specific log decryption | REMOVE | Product-specific concern outside this package |
| Doctor, docs, benchmarks, evals and tests | REDESIGN | Operational documentation and honest validation |

Concrete reference evidence: `scripts/tinker.ps1:183-190` reports direct work
without execution; `:203-242` manufactures worker outcomes and token counts;
`:260-268` saves fabricated verification into handoff/memory. The router invents
provider availability at `scripts/tinker-router.ps1:33-37` and fixes model names
at `:39-55`. Worktree removal uses force at `scripts/tinker-workspace.ps1:340`.
Memory has a positive baseline for unrelated entries at
`scripts/tinker-memory.ps1:227-248`. The eval runner's live path ignores exit
status at `scripts/test-evals.ps1:142-153`; its static summary overclaims at `:165`.
The reference test suite mutates conventions at `tests/tinker.tests.ps1:950-962`,
so it was inspected rather than executed in place.

## 2026-09-24: the in-app runtime

A task whose scope included architecture reversed four earlier decisions for one
concrete need: teammates used from inside Claude Code, Codex and Antigravity, in any
product project, without a terminal. Turn-one context, enforcement on the tool loop
and presence cannot come from instructions.

| Earlier decision | Change | Why hooks, not instructions |
| --- | --- | --- |
| No hooks | Lifecycle hooks run by each host's own loop; still no daemon, launcher, database or scheduler | Context at session start, presence at turn boundaries |
| Approvals replaced by host permissions | PreToolUse gate on the safety list; never-grantable tamper list | A hook deny binds even in bypass modes |
| Scoped notes only | Turn one lists validated note paths and open checkpoint ids for the current repository | No bodies, free text or scoring enter context |
| No installer; start in this checkout | Opt-in user-level installer through each host's CLI; project mode remains | The team must load in any project |
