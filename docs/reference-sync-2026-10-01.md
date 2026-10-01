# Workflow and verification improvements: 2026-10-01

Tinker is a general-purpose framework for Claude Code, Codex and Antigravity.
These changes strengthen existing guidance without requiring a particular tool,
repository, domain, task type or optional integration.

## Changes and purpose

| Change | Purpose and implementation |
| --- | --- |
| Exact Git checkout and metadata-directory trust | Local clones can validate the source's `.git` directory separately from its checkout. The optional Buzz kit trusts only explicit mounted checkout paths and their metadata directories. A real-Git regression also checks that unrelated repositories stay rejected. |
| Portable learning proposals | [Knowledge policy](../policies/knowledge.md) and the team skill keep raw task evidence local. Shared improvements cite repository-relative paths, symbols and revisions that another contributor can verify. Applying, committing and installing still need their own authorization. |
| Selected domain guidance for questions | The Lead charter and knowledge policy require reading applicable selected packs before answering questions as well as running workflows. Selection comes from the user or trusted repository guidance. All-host regression cases cover both routes; no team registry or inferred pack selection is introduced. |
| Minimal edits | [Workspace policy](../policies/workspace.md) requires preserving encoding and line endings and inspecting small edits for unrelated normalization. Repository formatter conventions still apply. |
| Current branch evidence | New worktree bases come from current repository evidence rather than an assumed branch name or a surviving obsolete remote ref. |
| CI and delivery evidence | [Evidence policy](../policies/evidence.md) separates configured, required and observed checks. CI covers only what ran. Delivery claims need matching deployed revision/artifact evidence; inaccessible checks remain unverified. |
| Failure attribution | A flaky-test claim needs matching failure/history evidence. Keep both the original failure and retry result; remote retries still require authorization. |

The installer, hooks and provider-specific entry points remain intact. Native
Claude Code, Codex and Antigravity use works independently of the optional Buzz kit.
Organization registries, database procedures, business rules, fixed model choices,
mandatory graph refresh and product deployment recipes are outside core defaults.

## Verification

The original implementation ran `python -m unittest discover -s tests -v`: 245
tests, 244 passed and one skipped because Windows denied creation of the evidence
grader's symlink fixture. This covered all-host installer rendering and hooks,
canonical entry points, evaluation tooling, Buzz flows and the real Git regression.
A skill size-budget failure was corrected before the final successful run.
All 33 generated adapter/pack files matched their canonical sources; held-out
cases were unchanged and `git diff --check` passed.

`claude plugin validate --json .` succeeded with no errors and advisory warnings
about absent author metadata and root `CLAUDE.md` not being shipped plugin context.
CLI availability was observed for Claude Code 2.1.274 and Codex 0.146.0.

These checks do not establish live model compliance. The question and learning
scenarios require observed runs in each host; a live host acceptance suite and
rebuilt Buzz container remain unverified. Reference names in documentation and
test fixtures were subsequently replaced with generic descriptions and sample
repositories; the package guard checks for built-in product/team registries.
