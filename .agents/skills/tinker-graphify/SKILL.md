---
name: tinker-graphify
description: Build or inspect clean-commit baseline and linked-worktree Graphify graphs on demand for an explicit graph request or justified broad topology question.
---

# Graphify a clean Git worktree

Use this skill only for an explicit graph request or a broad topology question
that source search cannot answer. Worktree creation, a new request and a narrow
code question do not trigger indexing. Resolve the exact repository and read
its instructions and Git status first. Use the shared
`scripts/graphify_project.py` helper from the Tinker checkout in every host.
It writes only below this package's ignored `.tinker/graphs/` directory;
never write Graphify output to a product checkout or into another tool's graph state.

The primary checkout must be clean, including staged, unstaged and untracked
files, and on the baseline branch you pass with `--baseline-branch`: confirm it
from the repository (its default or integration branch), never from its name.
No repository has a built-in default. `status` without the option checks the
branch the baseline recorded. The helper does not fetch. It refreshes that
baseline before indexing a linked worktree. The
worktree must be registered in `git worktree list --porcelain`, selected by
`--worktree-path <absolute-path>` or by a `--ticket` that matches exactly one
path or branch, and clean at its committed `HEAD`. A dirty worktree is
unavailable until commit and reindex. Selection never falls back to the
primary checkout. Extraction uses a temporary detached checkout of the commit
and removes it afterward; the live worktree is never scanned.

```text
python scripts/graphify_project.py <absolute-primary-path> --worktree-path <absolute-worktree-path> --baseline-branch <branch>
python scripts/graphify_project.py <absolute-primary-path> --action status --worktree-path <absolute-worktree-path>
python scripts/graphify_project.py <absolute-primary-path> --action query --worktree-path <absolute-worktree-path> --query "<question>" --budget 1200
python scripts/graphify_project.py <absolute-primary-path> --action cleanup --worktree-path <absolute-worktree-path>
```

For baseline-only indexing, omit the selector and keep `--baseline-branch`. Inspect the helper's exit status and returned paths. Use query
and handoff links only when `status` returns `verified: true` for that
selected worktree. Never substitute an older or baseline graph. A baseline
advance alone does not invalidate an unchanged worktree graph. Check query
conclusions against current source; a bounded budget does not make an
oversized graph loadable.

First worktree indexing copies the baseline `graph.json` and
`manifest.json`; later updates use that worktree's own files. No links are
used. Cleanup removes only transient `cache/` and retains graphs, manifests,
renders, revision metadata and legacy graph directories. If Python 3.11+ or
the optional Graphify CLI is unavailable, or extraction fails, report that
status and continue with ordinary source evidence. Code-only extraction is
local AST work; include semantic content only after checking its model and
data path. Do not install hooks, watchers or global graph registration.
