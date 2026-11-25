# Engineering skills: study and maintenance

Study of 2026-11-19. Questions: are superpowers and ponytail still installed, does
backend work go through them, and which other well-known best-practice repositories
are worth using? The rules live in [engineering skills](../policies/engineering-skills.md).
This document holds the evidence, the decisions and the upkeep.

## What was found

- **Installed and enabled** in `~/.claude/settings.json`: `superpowers@claude-plugins-official`
  7.0.2 (commit `22f0b463e7a5e579904dd6211a520321035526f7`, the latest release) and
  `ponytail@ponytail` 4.9.0 (commit `356918eba965ee1eac64bd3a7f0dd02108350de5`).
- **Ponytail 5.3.3** (2026-10-29) was read on 2026-11-19: **stay on 4.9.0**. Its
  second hook file (`hooks/claude-band.json`) runs the "band" module on every tool call
  and turn in Claude Code 2.1.290 and later (2.1.311 here), and no setting turns that
  module off short of disabling the plugin. Its `ledger` option is on by default and
  appends a row per turn, with the task's name or first prompt, to
  `~/.config/ponytail/band/<project>.csv`, which nothing prunes. `ponytail-review` now
  triggers on any review request, competing with Tinker's review route, and the skill
  drops its "not for non-coding" exclusion and adds a per-reply rule that clashes with
  Tinker's voice. The `ponytail` marketplace has no auto-update, so 4.9.0 stays until
  someone runs `claude plugin update`. To upgrade later: set `ledger` off and leave
  `webhookUrl` empty in the plugin's options, re-read the band hooks, and re-check the
  review trigger against [the policy](../policies/engineering-skills.md).
- **Backend work was not gated.** Implement, investigate and review never named a
  skill. Superpowers' session rule ("invoke any skill with a 1% chance") and ponytail's
  always-on hook made them ambient: used when the model chose to, skipped otherwise,
  and in conflict with Tinker's own routing for plans, branches and helpers.

## Decisions

| Repository | Verdict | How Tinker uses it |
| --- | --- | --- |
| obra/superpowers | Route five skills at named steps | Test first, systematic debugging, verification, receiving review. Planning, worktree, branch-finishing and helper-dispatch skills stay unrouted: they commit plan files, create branches or start agents by their own rules |
| DietrichGebert/ponytail | Route two skills, stay on 4.9.0 | `ponytail` when choosing the change, `ponytail-review` for the review's simplicity pass. 5.3.3 waits (above) |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | Two skills, pinned to `8c99fa36d90068c82d547f7c12a9d67a3e95f4ee` (0.6.17) | `security-and-hardening` at trust boundaries and in review; `deprecation-and-migration` for removals and schema changes. Its observability skill writes runbooks into the product, so its rules are restated in the policy instead |
| [trailofbits/skills](https://github.com/trailofbits/skills) | One skill, pinned to `149d7b21f4067765b82e67029730b42d228ef4b4` | `sharp-edges` when an API, configuration option or interface makes security choices for its users. It declares `allowed-tools: Read Grep Glob` and ships only Markdown references. The skills CLI installs it from its nested `plugins/sharp-edges/skills/` path; its CC-BY-SA licence means Tinker links it and never copies its text. Its `sharp-edges-analyzer` agent is not installed, and the skill works without it |
| Claude Code's own skills | Route one, nothing to pin | `claude-approvals` for `.claude/approvals.yml` and `.claude/classifiers/`. The host ships it, so other hosts apply the policy's fallback |
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

The pinned skills (`security-and-hardening`, `deprecation-and-migration` and
`sharp-edges`, beside the design skills) install for every app with:

```bash
python scripts/install_apps.py --skills --dry-run   # shows the npx commands
python scripts/install_apps.py --skills             # or: --app claude|codex|antigravity
```

The pins sit in `SKILL_SOURCES`, and their hashes in `skills-lock.json`; a test fails
when the two disagree. The skills CLI keeps one copy in `~/.agents/skills/` and links
each app's folder to it. A hand copy from before 2026-11-19 in
`~/.claude/skills/<name>/` (with a `SOURCE.md`) blocks that link: move it away before
re-running the installer. At `8c99fa3`, `security-and-hardening` also ships
`references/hardening-patterns.md`, which the hand copy lacked.

## Upkeep

A [pin check](design-skills.md#pin-check), on request, compares each pin with upstream. A skill bump follows
[bumping a skill pin](design-skills.md#bumping-a-skill-pin): read the diff, run the
pinned scratch install, copy its lock entries, and change `SKILL_SOURCES`. A plugin
whose new version adds hooks, telemetry, network calls or writes outside the product
waits for a review first. Rolling back is a bump to the previous commit.
