---
name: tinker-artifacts
description: Produce engineering artifacts - user stories, documentation, diagrams (Mermaid, PlantUML, archify, ASCII), ADRs and release notes - as Markdown by default, then offer GitHub issues or a project board for stories. Not for product code, defect fixes, reviews or discovery.
---

# Produce an engineering artifact

Resolve this package's AGENTS.md (`AGENTS.md` in the Tinker checkout) and load the
Technical Writer (`roles/technical-writer.md` in the Tinker checkout) charter, or the
Product Manager (`roles/product-manager.md` in the Tinker checkout) for stories. Unclear scope
needs shape (`.agents/skills/tinker-shape/SKILL.md` in the Tinker checkout) first; code changes need
implement (`.agents/skills/tinker-implement/SKILL.md` in the Tinker checkout).

1. Identify the artifact, audience, target repository and destination. The default
   is a Markdown file: a path the user named, else one that follows the repository's
   docs layout; state the path before writing. Ground content in current source,
   docs and history, cite files, and label assumptions and illustrative commands.
2. Stories follow the user story template (`templates/user-story.md` in the Tinker checkout),
   decisions the ADR template (`templates/adr.md` in the Tinker checkout). Release notes come from
   `git log <from>..<to>`: user-facing changes grouped by kind, nothing invented.
3. Diagrams: use the format the user names. Otherwise follow the repository (`.puml`
   files mean PlantUML, `.mmd` or mermaid blocks mean Mermaid); GitHub or GitLab
   Markdown means Mermaid; a terminal, code comment or plain text means ASCII; a
   standalone, checked HTML architecture page means archify. Still ambiguous: ask
   once, with a recommendation. Validate with an installed tool only (`mmdc`,
   `plantuml -checkonly`, archify `finalize`); otherwise report `not-verified`.
   Never send diagram source to a public rendering server or install a tool.
4. Write only the requested files, preserving user changes, and reread them. Report
   paths, sources used, validation and gaps.
5. Then, for stories, ask whether to create GitHub issues and/or add them to a
   GitHub Project board. That changes remote items: first show the repository,
   board, and each title, body file and label, and act only on explicit approval.
   Prefer one `gh issue create --repo <owner/repo> --title <t> --body-file <story>`
   per story, with `--project <board>` when wanted; board-only drafts use
   `gh project item-create`. Report created URLs. If `gh` is missing, signed out or
   lacks the `project` scope, stop: the Markdown stays the result, and only the user
   runs `gh auth login` or `gh auth refresh -s project`.

Other artifacts follow the same flow: runbooks, PR descriptions, test plans and
onboarding guides. Publishing anything else, such as a GitHub release or wiki page,
needs its own explicit approval.
