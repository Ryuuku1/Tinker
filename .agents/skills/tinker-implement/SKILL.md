---
name: tinker-implement
description: Implement a requested feature or refactor in an identified repository. Use for code changes with acceptance criteria, not questions or read-only reviews.
---

# Implement

Resolve this package's [AGENTS.md](../../../AGENTS.md) and its applicable policies
if not already loaded. Read the target repository's rules and existing user diff,
then do the [task start](../../../policies/workspace.md#task-start): its
`## Agent playbook` section, the latest base and the graph when it says `auto`.

1. Translate the request into observable acceptance criteria. Inspect the owning
   symbols, relevant callers and an existing analogous implementation. Ask only
   for missing information that blocks a safe result.
2. Choose the smallest safe change, climbing this ladder and stopping at the first
   rung that holds: does the code need to exist at all; does the codebase already
   have it; does the standard library or an existing dependency cover it; only then
   write new code. Never add a dependency for what those cover, and never trim
   validation, error handling, security or accessibility to save lines. State a
   short plan for multi-step work; avoid abstractions created merely for the ticket.
3. Change only the required code and relevant behavioral tests. Prefer a failing
   test before changing behavior when useful; do not add tests that only mirror
   wording or trivial implementation details. Inspect dependency, generated-file
   and schema effects when present.
4. Run the playbook's gates, narrowest first; widen only for shared contracts or
   unresolved risk. Read exit status and test summary, investigate failures and
   keep them in the outcome; a failed, unavailable or zero-test gate blocks a
   "done" claim. Use [evidence policy](../../../policies/evidence.md). For a
   changed UI, API or CLI flow, verify the running application when relevant and
   possible, per [application verification](../../../policies/app-verification.md).
5. Inspect the final diff against criteria and the original user changes. Request
   an independent review only when the risk justifies it and delegation permits.
   Fix material findings and reverify affected behavior.
6. Leave the deliverable as the playbook says; commit only when authorized. Return
   actual changes, verification, limitations and a proposed commit message in the
   repository's style. Complete all authorized local work; prepare a concrete
   result before asking about a consequential action.
7. End with the [retro](../../../policies/learning.md#retro).

Ordinary testing belongs to the implementer. No mandatory specialist, explainer,
report file, model choice or remote publication is part of this workflow.
