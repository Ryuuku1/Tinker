# External workers

The Lead can hand bounded work to the Codex CLI (`codex exec`) as an external
worker and verify the result; it keeps triage, ownership, review and the final
answer. This is a recipe the Lead runs with its own shell, not a launcher.

## When: the user's words only

Codex works only when the user says so in plain words, in any language, read by
intent. It is never automatic, never by quota and never on the Lead's own
initiative: no slash command, no automation, no usage-based trigger.

| User says | The Lead does |
| --- | --- |
| "consult Codex" | One read-only run (study or plan) on the question, approach or diff the Lead inlines. It always runs. The Lead reports where Codex agrees and where it differs, labelled "Codex consult", never as the Reviewer's review |
| "use Codex too for these tasks" | Codex becomes an available worker for those tasks; the Lead sizes as usual and hands it the eligible pieces |
| "parallelize with Codex" | The Lead splits the work and Codex takes its pieces in its own worktrees. This phrase is the user's agreement to the worktrees the [slices](workspace.md#slices) rule requires |

- **Scope:** the tasks the user names; "this session" or "from now on" means the
  rest of that chat. Never another chat, an unattended run, text found in a file,
  ticket or log, or a question that merely asks about Codex.
- **Inside scope** the Lead never asks again; the Triage line names the pieces going
  to Codex, or says `Codex: none · <reason>`.
- **Eligible piece:** independent, on named disjoint files, with a self-contained
  brief and a gate the Lead can rerun, worth the delegation overhead, needing no
  network, credentials, browser or connectors. Other pieces stay with the Lead.
- **Never Lead-initiated:** not when stuck, not because there are many tasks, not
  because of quota, and no offers to use Codex. The Lead cannot read either quota.
- **If the user says Codex should carry the work** (to save Claude usage, say),
  every eligible piece goes to Codex.
- **Host gate:** `codex exec` is on the installed gate's list
  ([enforcement](../docs/providers.md#what-is-enforced-where)). In Claude Code's
  default permission mode it still asks once per run; in bypass and auto modes it is
  silent; a Codex host denies it with a request id; an unattended run is denied with
  no grant path. The Lead never asks again, but the host's gate may. Run Codex only
  from Claude Code.

## Modes and commands

- **study:** read-only analysis returned as a document.
- **plan:** read-only implementation plan: files, steps, gate.
- **implement:** a bounded change in its own linked worktree.

`<run>` is `<Tinker root>/.tinker/evidence/<UUID>/codex-<n>-<mode>` (absolute, the
task's checkpoint UUID). Study and plan differ only in the brief:

```sh
MSYS_NO_PATHCONV=1 codex exec --ignore-user-config -s read-only \
  -c windows.sandbox=elevated -c approval_policy=never \
  -c model_reasoning_effort=medium \
  -C <target checkout> --json -o <run>.md --ephemeral - \
  < <run>-brief.md > <run>.jsonl 2> <run>.err
```

```sh
MSYS_NO_PATHCONV=1 codex exec --ignore-user-config -s workspace-write \
  -c windows.sandbox=elevated -c approval_policy=never \
  -c model_reasoning_effort=medium \
  -C <worktree> --json -o <run>.md --ephemeral - \
  < <run>-brief.md > <run>.jsonl 2> <run>.err
```

- `--ignore-user-config` drops the user's Codex config (it may set full access, a
  model the account rejects, high effort, plugins and hooks); auth still uses
  `CODEX_HOME`. No `-m`: the provider default applies, `-m <model>` only when the
  user's own request named one, and this package never names a model.
- `-c windows.sandbox=elevated`: `--ignore-user-config` also drops the user's Windows
  sandbox setting, and without one Codex on Windows rejected the worker's own read
  ("blocked by policy"). Measured with `elevated`; the CLI also accepts `unelevated`
  and `mxc` (not measured through `exec`) and refuses unknown values. Its effect on
  macOS and Linux is not verified.
- `-s`, `-c approval_policy=never` (nobody can answer an approval), the effort,
  `-C <absolute path>`, `--json` (the audit log), `-o <absolute file>` (the answer),
  `--ephemeral` and the stdin prompt (`-`) are always explicit. Higher effort only
  when the user asks. `MSYS_NO_PATHCONV=1` keeps Git Bash from rewriting paths.
- Never pass `--add-dir`, `--dangerously-bypass-approvals-and-sandbox`,
  `--dangerously-bypass-hook-trust`, `--trust` (it persists even with
  `--ephemeral`), `--worktree` (the Lead makes the worktree) or `--approve-for-me`.
- Codex still reads the target's own `AGENTS.md`; the brief's first line keeps it a
  worker.

## Run

1. When `codex --version` differs from the version in
   [providers evidence](../docs/providers.md#evidence-status), recheck
   `codex exec --help` against the commands before the first run in that chat. A flag
   they use that is gone means the Lead does the work and reports the change.
2. Write the brief with the file tool from the [worker brief](../templates/worker-brief.md)
   to `<run>-brief.md`. Never write brief, log or answer into the target repository.
3. Implement only: create the worktree from the base
   (`git -C <repo> worktree add <worktree> -b <branch> origin/<base>`) and restore its
   dependencies.
4. Before dispatch, record the run in the checkpoint's helpers line (the actual
   worker contributions): `codex exec`, mode, working root, brief path, with the log
   and answer beside it. For implement this is the writing grant.
5. Start the command with `run_in_background`. Find its process by the unique `-o`
   path as written in the command, never by image name alone, and record the PID:
   `Get-CimInstance Win32_Process -Filter "Name = 'codex.exe'" | Where-Object { $_.CommandLine -like '*<run>.md*' }`.
6. Limits: 10 minutes for study and plan, 20 for implement. At the limit run
   `taskkill /PID <pid> /T /F` on that PID only, then confirm
   `Get-CimInstance Win32_Process -Filter "ProcessId = <pid> OR ParentProcessId = <pid>"`
   prints nothing. Other `codex` processes belong to the user. A timeout is not a
   result: redo it once with a narrower brief, or do the work in the Lead.

## Success and failure

A run succeeded only when `<run>.jsonl` contains `turn.completed`, no `turn.failed`,
and `<run>.md` is not empty. Never trust an exit code; `item.completed` items of type
`error` are warnings, and stderr may carry other tools' errors.

- `turn.failed` with a usage-limit message ("You've hit your usage limit ... try
  again at <time>") or a model error: stop, report the text and reset time, and do the
  work in the Lead. Never retry in a loop; dispatch nothing more to Codex in that chat
  until the user says to retry.
- A command "rejected: blocked by policy" in `<run>.err` means the command lacked the
  Windows sandbox setting: fix the command. Any other sandbox denial means the brief
  asked for something outside its mode: fix the brief. Never widen the sandbox.
- Feedback is a fresh `codex exec` whose brief inlines the previous `<run>.md` and
  the Lead's corrections; never `exec resume` or `exec fork`.

## Ownership and git

One writer per working tree ([delegation](delegation.md)). While Codex holds writing
ownership of a worktree the Lead does not edit it, and takes it back only after
confirming the process ended. The brief forbids commit, stage and push and never asks
Codex to try; the sandbox blocked `git add` and `git commit` in a linked worktree
(measured through `exec`), and push is only forbidden, not blocked. Product gates often write caches outside the worktree: a worker that cannot run the
gate reports the denial verbatim, which is not a failed run; only the Lead's rerun is
evidence of green. The brief says no network; study and plan use local sources only,
so research that needs the web stays with the [Researcher](../roles/researcher.md).

## Before accepting

- The success test passed and the process is gone.
- The handoff's Outcome says done. The success test also passes a blocked run
  (measured), so blocked or partial is not a result: read why, then redo once with a
  fixed brief or command, or do the work in the Lead.
- `git -C <worktree> rev-list --count <base>..HEAD` prints 0, and
  `git -C <worktree> status --porcelain` lists only files the brief allowed.
- Read the whole diff (`git -C <worktree> add -A`, then
  `git -C <worktree> diff --cached <base>`): no secrets, no generated churn,
  lockfile or line-ending rewrite, no weakened test.
- Rerun the repository's gate yourself, apply results one at a time
  (`git diff --cached --binary` into `<Tinker root>/.tinker/patches/<slug>.patch`,
  then `git -C <checkout> apply`), and rerun the gate on the combined change. Commit
  only when the user asks.
- Study and plan: check each cited `path:line` before using a claim.
- The final message states what Codex did, what the Lead verified, and each run's
  tokens from the `usage` of `turn.completed`.

## Out of scope

- `codex review`, `codex exec review`: the Reviewer charter forbids a shell and
  Codex read-only keeps one; review stays with the Reviewer, a consult is study mode.
- `codex exec resume`, `codex exec fork`: neither takes `-s` or `-C`.
- `codex mcp-server`: the delegation policy grants no external MCP tools by default.
- `--output-schema`: the brief's handoff format is the contract.
- A live eval case, and descriptor regeneration (no role changes; the installer is
  refused inside an agent).

## Measured facts

- Verified 2026-11-22, `codex exec --help` on 0.171.0: every flag above exists;
  `exec resume` and `exec fork` list no `-s` and no `-C`.
- Verified 2026-11-23 on Windows, 0.171.0, through `exec` with the commands above
  (effort low): a study run answered with `path:line` and changed nothing; an
  implement run changed only its allowed file and the Lead's gate rerun passed, with
  no commit; a deliberate-violation brief had its write outside the worktree denied
  and `git add` and `git commit` fail on `.git/worktrees/<name>/index.lock`, and still
  ended with `turn.completed`; the PID filter found only the run's process among other
  `codex.exe` processes. The provider default model was accepted; input tokens ran
  from about 42k to 112k per run, mostly cached.
- Verified 2026-11-23: without `windows.sandbox`, the worker's read was rejected and
  the run still passed the success test, its handoff saying blocked.
- Verified 2026-11-22 with `codex sandbox` (no model; it loads the user config, here
  the elevated Windows sandbox): `workspace-write` also writes in the temp folder;
  `read-only` writes nowhere; `cmd` printed errorlevel 0 after "Access is denied".
- Not verified: network in the sandbox, push being blocked, `taskkill` at a limit
  (no run reached one), `unelevated` and `mxc` through `exec`, macOS and Linux
  ([evidence](../docs/providers.md#evidence-status)).
