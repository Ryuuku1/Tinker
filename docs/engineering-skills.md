# Engineering skills: study and maintenance

Study of 2026-11-19. Questions: are superpowers and ponytail still installed, does
backend work go through them, and which other well-known best-practice repositories
are worth using? The rules live in [engineering skills](../policies/engineering-skills.md).
This document holds the evidence, the decisions and the upkeep.

## What was found

- **Installed and enabled** in `~/.claude/settings.json`: `superpowers@claude-plugins-official`
  7.0.2 (commit `22f0b463e7a5e579904dd6211a520321035526f7`, the latest release) and
  `ponytail@ponytail` 4.9.0 (commit `356918eba965ee1eac64bd3a7f0dd02108350de5`).
- **Ponytail 5.3.3 exists** (2026-10-29) and is not reviewed. It adds a "band" module
  that writes a row per turn to `~/.config/ponytail/band/<project>.csv`, with optional
  webhook settings. Stay on 4.9.0 until that code is read.
- **Backend work was not gated.** Implement, investigate and review never named a
  skill. Superpowers' session rule ("invoke any skill with a 1% chance") and ponytail's
  always-on hook made them ambient: used when the model chose to, skipped otherwise,
  and in conflict with Tinker's own routing for plans, branches and helpers.

## Decisions

| Repository | Verdict | How Tinker uses it |
| --- | --- | --- |
| obra/superpowers | Route five skills at named steps | Test first, systematic debugging, verification, receiving review. Planning, worktree, branch-finishing and helper-dispatch skills stay unrouted: they commit plan files, create branches or start agents by their own rules |
| DietrichGebert/ponytail | Route two skills | `ponytail` when choosing the change, `ponytail-review` for the review's simplicity pass |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | Two skills, pinned to `8c99fa36d90068c82d547f7c12a9d67a3e95f4ee` (0.6.17) | `security-and-hardening` at trust boundaries and in review; `deprecation-and-migration` for removals and schema changes. Its observability skill writes runbooks into the product, so its rules are restated in the policy instead |
| trailofbits/skills | Not now | `sharp-edges` (read-only: dangerous defaults, configuration cliffs, silent failures) fits review, but the repository only offers marketplace installs of nested plugins, and its CC-BY-SA licence rules out copying text. Revisit at the next upgrade |
| anthropics/skills, mattpocock/skills, github/spec-kit, the Karpathy rules, garrytan/gstack, EveryInc/compound-engineering-plugin, wshobson/agents, humanlayer/12-factor-agents, SuperClaude, BMAD-METHOD, affaan-m/ECC | Skip | No backend practice, already covered by implement and ponytail, or a second framework that commits, pushes, opens pull requests, installs hooks or pins models |

Every routed skill has a fallback written in the policy, so a host without it still
applies the rule. The backend rules (security, removal, observability) apply whether
or not the skills are listed.

## Install

Plugins, in Claude Code:

```bash
claude plugin install superpowers@claude-plugins-official
claude plugin marketplace add dietrichgebert/ponytail && claude plugin install ponytail@ponytail
```

The two addyosmani skills are plain Markdown. Copy each folder unmodified from the
pinned commit into `~/.claude/skills/<name>/` with the repository's `LICENSE` and a
`SOURCE.md` that records the commit and SHA-256 of each file:

| Skill | `SKILL.md` SHA-256 at `8c99fa3` |
| --- | --- |
| `security-and-hardening` | `f78655c64329b53ee216c9bc1b8c01f6cd40d2e9caad35944f4b0dbed8fd16b7` |
| `deprecation-and-migration` | `1896d7db836fc067e2856739664db9ff5bb642526fdff2126d08ec0d588da4b7` |

`LICENSE` is `6f202f8bd568cd730dbb2b0d1f8e243bc74c2fa1f64dbce9b2c7ea08bd5c9fd7`. Codex and
Antigravity see these only when copied into their own user skills folder; otherwise
they apply the fallback.

## Upkeep

The monthly upgrade routine checks each pin. For a bump: read the diff between the
pinned and the new commit, re-run the copy, compare the hashes, and update this
document and each `SOURCE.md`. A plugin whose new version adds hooks, telemetry,
network calls or writes outside the product waits for a review, as ponytail 5.x does.
Rolling back is the same copy at the previous commit.
