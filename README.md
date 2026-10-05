# Tinker

Your software team inside **Codex, Claude Code or Antigravity**. Open this project,
give the Lead an outcome and identify the product repository. The Lead coordinates
relevant specialists, completes authorized work and returns artifacts and evidence.
Nothing runs outside your AI app. Optionally [install it into the apps](#use-it-in-any-project)
so the team, approvals and status work in every product project.

## Start using it

Open this checkout as the project in your chosen host. Authenticate through the
host normally and grant access to the product folder using its native controls.

| Host | Start | Check discovery |
| --- | --- | --- |
| Codex app | Add/open this folder as a project and start a task | Inspect loaded project instructions, skills and native agents |
| Codex CLI | `codex --add-dir <absolute-product-path>` from this checkout | Inspect loaded project guidance and available agents |
| Claude Code | `claude --plugin-dir . --add-dir <absolute-product-path>` from this checkout | Inspect memory, skills and agents using the installed host's views |
| Antigravity | Open this folder as a project; grant product access through native controls | Inspect Customizations for the always-on rule, seven skills and eight specialists |

The project must be trusted for the host to load local configuration. Directory
access alone does not load product instructions; the Lead reads them.
See [provider setup and verification limits](docs/providers.md).

Then send an ordinary request, replacing the example path:

```text
Team, implement customer invitations in <absolute-product-path>.
Work through design, implementation, testing and review. Preserve my existing edits.

Designer, propose a clearer onboarding flow for <absolute-product-path>.
Deliver the design only.

Technical Writer, improve the setup guide in <absolute-product-path>.

Delivery Engineer, prepare this change for release. Do not publish yet.
```

For a new product, give its desired destination and acceptance criteria. No slash
command, ticket identifier or role naming is required. You may address any
specialist by role in normal language.

## Your team

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

These are persistent role instructions. Real workers are native host agents, used
only when useful. Several specialists can work sequentially, with at most two
active helpers, one writer including the Lead, and no recursive delegation.
Small jobs can stay with the Lead. Unavailable helpers mean transparent Lead work;
role switching is never presented as independent review.

Seven canonical skills cover shaping, implementation, investigation, review,
engineering artifacts (user stories, documentation, diagrams, ADRs and release
notes, saved as Markdown first, with GitHub issues or a project board only on
approval), on-demand Graphify graph maintenance, and team status, schedules,
approvals and learning reviews. Research, testing and delivery use their relevant
charters directly. Changes to a running UI, API or CLI are verified per a shared
[application verification](policies/app-verification.md) reference when relevant.
Optional [domain packs](templates/domain-pack.md) load only when you name one or your
repository's instructions link it.
All three hosts share the source instructions; native descriptors adapt discovery
and requested tool access. Models and authentication remain host-owned.

## On-demand Graphify graphs

Use Graphify for an explicit graph request or a broad topology question that
source inspection cannot settle. Worktree creation and ordinary requests do not
run it. The helper keeps a baseline and one graph per registered linked worktree
under this package's ignored `.tinker/graphs/` directory. Existing flat
graph directories are retained. Product repositories receive no graph output.

The primary checkout must be clean and on the baseline branch you pass with
`--baseline-branch`; no repository has a built-in default, so earlier invocations
that relied on one now name their branch. `status` without the option checks the
branch the baseline recorded. The helper does not fetch. It refreshes that baseline
before indexing a selected worktree's clean committed `HEAD`. Select the
worktree by absolute path or by a ticket matching exactly one registered path
or branch. Dirty worktrees are unavailable until committed and reindexed. A
baseline advance leaves an unchanged worktree graph verified. Extraction reads
a temporary detached checkout of each commit, so ignored or hidden local files
cannot enter a graph; the temporary checkout is removed afterward.

```text
python scripts/graphify_project.py <absolute-primary-path> --baseline-branch <branch>
python scripts/graphify_project.py <absolute-primary-path> --worktree-path <absolute-worktree-path> --baseline-branch <branch>
python scripts/graphify_project.py <absolute-primary-path> --action status --worktree-path <absolute-worktree-path>
python scripts/graphify_project.py <absolute-primary-path> --action query --worktree-path <absolute-worktree-path> --query "<topology question>" --budget 1200
python scripts/graphify_project.py <absolute-primary-path> --action cleanup --worktree-path <absolute-worktree-path>
```

The `status` response exposes graph and HTML paths only when the selected
worktree graph matches its clean `HEAD` and recorded seed baseline commit.
Use those verified paths for queries and handoff links. Queries never fall back
to a baseline or older graph. Cleanup removes only that worktree's transient
`cache/`; graph files, renders, revision metadata and legacy directories remain.

Python 3.11+ and Graphify are prerequisites for indexing. Install the official
[`graphifyy` package](https://github.com/Graphify-Labs/graphify#install) using its
documented method, for example `uv tool install graphifyy`, then check
`graphify --version`. If either tool is unavailable or extraction fails, the Lead
continues the request using source files and reports the graph status. A request
to include documents or media may need a model backend; discuss its data path
before running that scan. Graph creation does not install hooks or modify global
assistant configuration.

## Use it in any project

Install Tinker at user level so every chat in the apps starts with the Lead,
this repository's validated notes and open checkpoints, and a native approval gate.
Run it yourself, in a terminal, from this checkout:

```text
python scripts/install_apps.py --dry-run
python scripts/install_apps.py
python scripts/install_apps.py --uninstall
```

It renders a small bundle under `~/.tinker/`, stages and self-tests it, and
registers it with `claude` and `codex` and as an Antigravity plugin. It replaces or
deletes only files it recorded with their hash, restores the previous files if an
update fails, and reports each app separately: one app can be current while another
is stale or waiting for a recovery command. It refuses an app where another Tinker
installation is enabled, and a home whose records it did not write. After installing, trust the hooks in Codex's `/hooks`. Ask any chat for
"team status", to schedule a specialist, or to review recent lessons.
Force pushes, protected-branch pushes, branch deletion, discarding work, recursive
deletes, remote changes, publishing and credential changes need your approval;
scheduled runs cannot approve anything. Re-run the installer after pulling changes.
See [per-app details and limits](docs/providers.md#optional-user-level-install).

## Windows or Linux

Tinker's own scripts are Python and run on both. The optional [Buzz kit](integrations/buzz/kit/GUIDE.md) has a
PowerShell 7 version for Windows and a bash version for Debian and other Linux hosts, kept in step by tests. Tell
this checkout which one you use, once; the choice lives in the ignored `.tinker/platform.json`, so pulling new
versions never conflicts with it:

```text
python scripts/tinker_platform.py                 # show the platform in use (auto-detected until you set one)
python scripts/tinker_platform.py set linux       # or windows, or auto
python scripts/install_apps.py --platform linux   # the same, while installing into the apps
python scripts/tinker_platform.py kit setup --owner-npub <npub> --repository <path>   # that platform's kit script
```

`kit` takes the bash spelling of the options on both platforms and turns it into PowerShell parameters on Windows.
`TINKER_PLATFORM=windows|linux` overrides the stored choice for one command.

## Continue or switch hosts

Substantial or delegated work gets an isolated checkpoint under
`.tinker/tasks/<UUID>.md` in this checkout. The Lead gives you its exact path.
Ask: "Prepare this job for handoff and stop its helpers." After the old session is
paused or stopped, open this project in the other host and say:

```text
Continue the job from <absolute-checkpoint-path>. Recheck the repository state first.
```

The next host resumes work from evidence, not the other provider's conversation.
Never run two hosts on the same job simultaneously. Shared knowledge is selective,
source-backed Markdown under the package's ignored `.tinker/knowledge/` folder.
Checkpoints and knowledge stay out of product repositories and version control.

## Boundaries and validation

Local work proceeds within your request. Commits, pushes, publishing, deployment,
external messages and destructive actions need explicit authorization. Native
permissions enforce access; instructions alone are not a sandbox. The installed
gate classifies command text, so it guards against mistakes rather than sandboxing.
Scheduling uses the app's own scheduler; this package only validates the plan.

Run `python -m unittest discover -s tests -v` for package, grader and suite checks,
and `claude plugin validate --json .` for the Claude manifest. Python 3.11+ is
needed for these development checks and on-demand Graphify graphs.

The [evaluation guide](evals/README.md) separates synthetic tests from live behavior
and explains suite acceptance; no accepted live baseline exists yet.
A configured host is not automatically verified. See [architecture](docs/architecture.md)
and [extension guidance](docs/extending.md). Original Gemini CLI files remain as
secondary compatibility; they do not constitute Antigravity support.
