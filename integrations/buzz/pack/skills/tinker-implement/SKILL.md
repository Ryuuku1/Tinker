---
name: tinker-implement
description: Implement a requested feature or refactor in an identified repository. Use for code changes with acceptance criteria, not questions or read-only reviews.
---

# Implement

Resolve this package's AGENTS.md (`AGENTS.md` in the Tinker checkout) and its applicable policies
if not already loaded. Read the target repository's rules and existing user diff.

1. Translate the request into observable acceptance criteria. Inspect the owning
   symbols, relevant callers and an existing analogous implementation. Ask only
   for missing information that blocks a safe result.
2. Choose the smallest safe change. State a short plan for multi-step work; avoid
   architecture files and abstractions created merely for the ticket.
3. Change only the required code and relevant behavioral tests. Prefer a failing
   test before changing behavior when useful; do not add tests that only mirror
   wording or trivial implementation details. Inspect dependency, generated-file
   and schema effects when present.
4. Run appropriate focused checks. Read exit status and test summary, investigate
   failures and retain them in the outcome. Broaden testing only for unresolved
   risk or new evidence. Use evidence policy (`policies/evidence.md` in the Tinker checkout). For a
   changed UI, API or CLI flow, verify the running application when relevant and
   possible, per application verification (`policies/app-verification.md` in the Tinker checkout).
5. Inspect the final diff against criteria and the original user changes. Request
   an independent review only when the risk justifies it and delegation permits.
   Fix material findings and reverify affected behavior.
6. Return actual changes, verification and limitations. Complete all authorized
   local work; prepare a concrete result before asking about a consequential action.

Ordinary testing belongs to the implementer. No mandatory specialist, explainer,
report file, model choice or remote publication is part of this workflow.
