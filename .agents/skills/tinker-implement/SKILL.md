---
name: tinker-implement
description: Implement a requested feature, refactor or other edit, however small (one line too), in an identified repository. Not for questions or read-only reviews.
---

# Implement

Resolve this package's [AGENTS.md](../../../AGENTS.md) and its applicable policies
if not already loaded. Read the target repository's rules and existing user diff,
then do the [task start](../../../policies/workspace.md#task-start): its
`## Agent playbook` section, the latest base and the graph when it says `auto`.

1. Translate the request into observable acceptance criteria and list them before
   coding, with every attached design (mockup, screenshot, design file) opened before
   the first change. When a design and the text disagree, ask now; unattended, follow
   the design and record the disagreement. Inspect the owning symbols, relevant
   callers and an analogous implementation. Ask only for missing information
   that blocks a safe result. Check any access outside the repository (a database, a
   design file, a cloud resource) now with one cheap call; report a failure at once.
2. From here on follow [engineering skills](../../../policies/engineering-skills.md).
   Choose the smallest safe change: does the code need to exist; does the codebase,
   standard library or an existing dependency cover it; only then write new code. Never add a dependency for what those cover, and never trim
   validation, error handling, security or accessibility to save lines. State a
   short plan for multi-step work; no abstractions made only for the ticket.
   A change across areas the playbook gates separately, or of 8+ points, first gets
   [slices](../../../policies/workspace.md#slices) in its checkpoint, run one at a time.
3. Change only the required code and relevant behavioral tests. Behavior changes
   start with a failing test; no tests that only mirror wording or
   trivial implementation details. Inspect dependency, generated-file and schema
   effects when present.
4. Run the playbook's gates, narrowest first; widen only for shared contracts or
   unresolved risk. Investigate failures and keep them in the outcome; a failed,
   unavailable or zero-test gate blocks a "done" claim. Use
   [evidence policy](../../../policies/evidence.md). For a changed UI, API or CLI
   flow, verify the running application when possible, per
   [application verification](../../../policies/app-verification.md).
5. Tick each criterion with its evidence (a test, a command result, a screenshot
   compared with the design at the same viewport); one without evidence is unverified,
   never done. Inspect the final diff against the original user changes. Request an
   independent review only when the risk justifies it. Fix material findings and
   reverify affected behavior.
6. Leave the deliverable as the playbook says; commit only when authorized. Return
   actual changes, verification, limitations and a proposed commit message in the
   repository's style. Complete all authorized local work; prepare a concrete
   result before asking about a consequential action.
7. End with the [retro](../../../policies/retro.md): first save its lines, with
   the policy's front matter, to the Tinker root's
   `.tinker/retros/<yyyy-mm-dd>-<slug>-implement.md`, then close the final message
   with them.

Testing is the implementer's. No mandatory specialist, report file, model choice or
remote publication is part of this workflow.
