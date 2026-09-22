# Tools and context

Resolve the uncertainty using the cheapest adequate evidence: local status/diff,
targeted text/symbol search, relevant callers and language tooling, then focused
checks. For external or changing facts, use current official documentation; use
other primary sources when needed and label inference. Stop when the question is
answered. Do not impose a one-source rule when claims need different evidence.

For language tooling, validate changed symbols and types with headless compiler
diagnostics before full test runs, scoped to the changed project and preferring an
established repository script or LSP diagnostics when present:

- .NET/C#: `dotnet build -v minimal --no-incremental`
- TypeScript: `npx tsc --noEmit` with the repository's installed compiler, run as
  `npx --no tsc --noEmit`, `pnpm exec tsc --noEmit` or `yarn tsc --noEmit` so a
  missing compiler fails instead of downloading (plain `npx`/`npm exec` and `bunx`
  install by default); confirm the same runner's `tsc -v` matches the repository's
  locked version. A missing or mismatched compiler is `not-verified`, never an install
- Python: `pyright` or `mypy --no-error-summary`, which also hides the file count
- Rust: `cargo check --message-format short`
- Go: `go vet ./...`

A quiet zero exit counts only when the command covered the changed files, for
example `-p` with the leaf tsconfig in solution-style setups,
`cargo check --all-targets` when tests changed, or the features, build tags or
target platform (`--features`, `-tags`, `GOOS`, `--target`) that compile the
changed code; an unavailable target is `not-verified`. These can still write
build output or caches, so they need writing ownership. Diagnostics narrow a
problem quickly; they never replace the relevant tests.

When reading build or test output, drop banners, progress lines and out-of-scope
warnings such as `warning CSxxxx` or `warning TSxxxx`. Keep every actionable error,
failure block, stack trace and summary total verbatim, plus warnings the change
introduced or the task concerns. Say what was trimmed; see [evidence](evidence.md).

In review diffs, skip line-by-line reading of dependency lockfiles
(`package-lock.json`, `pnpm-lock.yaml`, `Cargo.lock`, `packages.lock.json`,
`bun.lockb`) and focus on source and tests, for example with a Git pathspec such
as `':!*package-lock.json'`. Still list lockfiles in the change inventory; inspect
them under [safety policy](safety.md) when dependencies are added, removed or
upgraded, or a lockfile changes without a matching manifest or task reason.

Use installed native tools before introducing adapters. Discover only needed
capabilities; scope MCP/CLI queries by repository, fields, time window and result
count. Tool availability does not grant permission. Do not automatically install
integrations, connect accounts, change models or switch providers after a failure.

Use [Graphify](../.agents/skills/tinker-graphify/SKILL.md) only when explicitly
requested or when source search leaves a justified broad topology question.
The helper requires a clean primary checkout on the baseline branch passed with
`--baseline-branch` (confirmed from the repository, never assumed from its name)
and, for a linked worktree, its clean committed HEAD. It refreshes the baseline
before indexing that worktree. Status, query and handoff links use only the
selected worktree's verified graph; a stale or dirty graph is unavailable.
If Graphify is unavailable or extraction fails, continue with ordinary source
evidence and report the status. Do not fetch, install hooks or index merely
because a worktree was created. Cleanup removes transient cache only.

Another tool may already keep a topology graph for the target. When topology needs
it, workers may inspect it read-only with bounded search instead of indexing. Treat
it as a snapshot: record its revision or date and confirm conclusions against
current source. Never index into, refresh or create Git hooks for another tool's graph.

A bounded output budget does not make an oversized graph queryable. Check the query
or tree result; if the installed tool rejects the graph, exclude generated sources
when supported or fall back to ordinary search.

Large repositories: inventory manifests and relevant subtrees, exclude generated
content from initial search, and expand deliberately. Still list generated/binary
and lockfile changes in the final diff. Keep source references in worker handoffs,
not repeated whole files. Delegate only under [delegation policy](delegation.md).
