# Agent playbook section

Copy the section below into the product repository's own `AGENTS.md` (or `CLAUDE.md`
when that is its only agent file), under the exact heading `## Agent playbook`. It
holds how this repository builds, verifies and delivers, so every task starts from the
same facts instead of rediscovering them. It travels with the repository and is
reviewed like any other change there. Write it in the repository's terms; never name
this package in it.

Keep each bullet a fact someone verified: an exact command, a branch, a path relative to
the repository root. Leave out what the repository's README or scripts already say
clearly; point to them instead. Mark an unverified line `(unverified)`.

```markdown
## Agent playbook

- Base branch: `main` for features and fixes. Releases branch from `<branch>`, if any.
- Gates, narrowest first:
  - Unit: `<exact command>` (from the repository root).
  - Build: `<exact command>`.
  - Full: `<exact command>`, only for shared contracts or before delivery.
- Deliverable and commits: <uncommitted changes | a commit on a feature branch>;
  messages follow <Conventional Commits | the existing log style>.
- Worktrees: <when to use one>; location `.claude/worktrees/<name>` (git-ignored).
- Live pass: <none | start `<command>`, ready when `<URL or log line>`, local
  identity `<how>`, stop `<command>`>.
- Graph: on-demand (or `auto` to refresh the Graphify graph at task start).
- Pitfalls:
  - <a mistake that cost time once, and how to avoid it>.
```

## Rules for the section

- Product rules stay where the repository keeps them; the section only points to them.
- It never widens permissions, selects another repository or overrides Tinker's
  safety and authorization rules. Commands in it are still checked before running.
- A missing section is normal. Discover gates from the repository, then offer the
  section as a proposed change; write it only when the user approves that change in
  that repository.
- Learning adds or changes one bullet at a time (see the
  [learning policy](../policies/learning.md)); never rewrite the section wholesale.
