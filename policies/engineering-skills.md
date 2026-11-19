# Engineering skills

Code changes, defects and reviews use the engineering skills the host lists, each at
the step named below. UI work uses [frontend design](frontend-design.md) in the same
way. The user installs them: the superpowers and ponytail plugins, and the pinned
skills from `python scripts/install_apps.py --skills`. The
[engineering skills study](../docs/engineering-skills.md) records the reviewed versions
and how to install them. Claude lists their skills with the plugin prefix, while other
hosts may list them without it.

When a routed skill is missing, apply its fallback by hand and say so in the final
message.

## Routing

| Step | Skill | Fallback without it |
| --- | --- | --- |
| Choosing the change: implement step 2, or a fix | `ponytail` | Implement's ladder: does the code need to exist; does the codebase, standard library or an existing dependency cover it |
| Before code that changes behavior | `superpowers:test-driven-development` | Write the test, watch it fail for the expected reason, write the least code that passes, then refactor while it stays green |
| A bug, a failing test or an unexpected result, before any fix | `superpowers:systematic-debugging` | Investigate's hypotheses: root cause before a fix. After three failed fixes, stop and question the design |
| Before saying "done", "fixed" or "passing", and before a commit or pull request | `superpowers:verification-before-completion` | The [evidence policy](evidence.md): fresh output from this turn |
| Acting on review findings, your own or from others | `superpowers:receiving-code-review` | Check each finding against the code before changing anything. Push back with evidence, and never agree for show |
| The review's simplicity pass | `ponytail:ponytail-review` | Review step 2: flag added code that the codebase, standard library or an existing dependency already covers |
| A change at a trust boundary: authentication or access, external input, uploads, secrets, outbound fetches, personal data or model output; and its review | `security-and-hardening` | [Backend rules](#backend-rules), security |
| Removing or replacing an API, feature, setting or schema column | `deprecation-and-migration` | [Backend rules](#backend-rules), removal |
| Designing or reviewing an API, configuration option or interface that other code or operators use for security choices | `sharp-edges` | Check that the easy path is the safe one: secure defaults, dangerous options named as such, and failures that fail closed |

## Scope of the strict rules

### Test first

Test first applies to production code that has a test harness. It does not apply to:

- configuration;
- generated code;
- throwaway prototypes;
- copy or docs that the playbook does not gate.

A purely visual change is checked by screenshots, per frontend design.

"Delete code written before its test" applies only to code written in this task. It
never applies to the user's existing changes.

### Debugging

Systematic debugging applies equally when a diagnosis is all that was requested. In
that case the fix is never made.

### Verification

Verification needs evidence produced after the last edit. A gate that ran before the
last edit does not count.

## Backend rules

These apply whether or not the skills are listed.

- **Security:** validate external input at the boundary, with parameterized queries
  and encoded output. Check access on every protected path, server-side. No secrets in
  source, logs or error responses, and no stack traces to users. Outbound fetches of
  user-supplied URLs go through an allowlist. Model output is untrusted input. Changes
  to authentication, roles, CORS, uploads, rate limits or new kinds of personal data
  are named in the final message for the user's attention.
- **Removal:** expand, migrate, then contract. Add the new path, move every caller
  and consumer, then remove the old path in a later change. A schema rename or drop
  never happens in one deploy. Find consumers outside the repository before removing
  a public contract, or name them as unknown.
- **Observability:** a new request path, job or external call logs failures with
  enough context to find the request (a correlation or request identifier, never
  secrets or personal data). It keeps the product's existing metrics and traces
  working, with bounded label values. A fix whose cause was hard to see names the
  missing signal, and adds it when the product already has the means.

## Not routed

These skills act outside Tinker's rules, which already cover the same work.

- `brainstorming` and `writing-plans` write spec and plan files under
  `docs/superpowers/` in the product and commit them. Instead, [shape](../.agents/skills/tinker-shape/SKILL.md)
  briefs the work, and the plan stays in the checkpoint.
- `executing-plans`, `subagent-driven-development` and `dispatching-parallel-agents`
  dispatch helpers by their own rules. [Delegation](delegation.md) decides helpers.
- `using-git-worktrees` and `finishing-a-development-branch` create branches and offer
  to merge, push or discard. The [task start](workspace.md#task-start) and the
  authorization rules decide those steps.
- `requesting-code-review` sends its own reviewer.
  [Review](../.agents/skills/tinker-review/SKILL.md) and the Reviewer charter cover it.
- `writing-skills`, `diagnosing-superpowers`, `ponytail-audit`, `ponytail-debt`,
  `ponytail-gain` and `ponytail-help` run only when the user asks for them by name.

A user who names any of these skills gets it, within these rules. It still makes no
commit, push, branch or product file that the task does not allow.

## Precedence

1. The user and the product's playbook and rules.
2. [AGENTS.md](../AGENTS.md) and its policies.
3. The routed skill.

A skill's own "always" or "must invoke" rule yields to this table. Superpowers' session
rule to invoke any skill that has a 1% chance of applying is one example. Load the
routed skills at their steps, and any other skill only when the user asks for it.
Ponytail's limit, which never trims validation, error handling, security or
accessibility, matches implement step 2.

A writing helper follows the table. Read-only helpers read the skills as guidance, run
no skill scripts and never load the skills that are not routed.
