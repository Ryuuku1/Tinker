---
name: tinker-shape
description: Shape a software idea or design request into a usable product brief, user flow and acceptance criteria, or grill the user on a plan until it is settled. Use for discovery, scope and design; not routine edits, debugging or code review.
---

# Shape a software request

Resolve this package's AGENTS.md (`AGENTS.md` in the Tinker checkout) and load only the relevant
Product Manager (`roles/product-manager.md` in the Tinker checkout) or
Designer (`roles/designer.md` in the Tinker checkout) charter. Honor the user's requested output:
an idea discussion does not authorize implementation.

1. Identify the outcome, audience and requested artifact. Inspect the existing
   product, target instructions and similar flows before asking discoverable
   questions. A new product needs an explicit destination before file creation.
2. Resolve only material uncertainties: goals, scope, constraints and consequential
   tradeoffs. State low-risk assumptions and keep independent work moving.
3. Propose the smallest useful approach. For genuine alternatives, compare their
   effects on the user and recommend one. Reuse the product's patterns and tools.
4. Deliver the relevant brief or design: intended behavior, in/out of scope,
   acceptance examples, relevant user flow and failure states, decisions and open
   blockers. Save a product artifact only when requested; otherwise return it in
   the conversation and record needed decisions in the isolated job checkpoint.
5. If the user already authorized implementation, hand the accepted requirements
   to implement (`.agents/skills/tinker-implement/SKILL.md` in the Tinker checkout) and continue without requesting
   the same permission again. Stop only for a material unresolved decision or
   an action outside the authorization. For design-only work, deliver the design.
6. End with the retro (`policies/learning.md` in the Tinker checkout).

## Grill mode

When the user asks to be grilled, or to stress-test or close the gaps in a plan:
walk the plan's decision tree, dependencies first. Ask one decision at a time
(a host's question tool may batch a few independent ones), each with your
recommended answer and its tradeoff. Answer from the code, docs or history
whatever they can settle, and say what you looked up; only real choices reach the
user. Keep a running list of settled decisions. Change nothing until the user
confirms the summary as shared understanding; then deliver the brief as in step 4.

Use actual native specialists only when they add value. The Lead adopting a role
does not constitute a separate teammate or independent validation.
