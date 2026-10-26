# Retros and eval-gated learning

Two parts: a short retro after each workflow, kept locally as evidence, and a learn
pass that turns that evidence into at most three small edits, kept only when the live
evaluation gate passes. Knowledge notes and candidates stay under the
[knowledge policy](knowledge.md); this policy covers changes to instructions.

## Retro

The implement, investigate, review and shape workflows end their final message with a
`Retro` section of at most five lines, and nothing follows it:

- What cost time or went wrong, if anything (at most two lines).
- Optionally one proposed delta edit: add or change one bullet, never rewrite a section,
  naming its destination: a Tinker skill, policy, role or template; the target
  repository's `## Agent playbook` section ([template](../templates/agent-playbook.md));
  or a local knowledge candidate. Do not apply it now.

Before the final message, save the same lines to the Tinker checkout's ignored
`.tinker/retros/<yyyy-mm-dd>-<ticket or 2-4 word slug>-<workflow>.md` (add `-2`, `-3`
when taken) with front matter `date`, `workflow`, `repository` (the folder name),
`ticket` when there is one and, for implement and investigate, `round`: 1 for a first
delivery, 2, 3 and so on when the user or a reviewer sent the work back (weekly
maintenance counts those as rework). Skip the file for a question answered without
edits or investigation, and say so when the session cannot write files. Retros never leave
this machine, but learn cites them in shared commits: no secrets, credentials,
personal or customer data, log or database excerpts, absolute paths or task-record
paths. Cite repository-relative paths, symbols, commands and ticket ids instead.

## Learn

A request such as "learn", "learn from recent work" or the front door's `learn [focus]`
authorizes steps 1-5 below, including the commit in step 5; nothing more. The live gate
needs the `claude` CLI; see the [evaluation guide](../evals/README.md).

1. **Evidence.** Retros dated in the last 30 days (newest first, filtered by the focus
   when given), open items of recent checkpoints under `.tinker/tasks/`, the latest
   weekly maintenance report and upgrade report under `.tinker/reports/` (the upgrade
   scan's release, model and practice proposals), and failing graders in the newest
   result under `evals/live/results/`. Pick at most three delta edits, each tied to its
   evidence; skip one whose bullet already exists. With nothing to pick, say so and stop.
2. **Route.** Edits to Tinker's own files continue below. A fact about a product
   repository becomes a proposed bullet for its `## Agent playbook` section, shown to the
   user as a change in that repository and written only on their approval there; a
   one-off fact stays a local knowledge candidate.
3. **Branch.** `git -C <root> status --porcelain` must print nothing; otherwise stop and
   say so. Then `git -C <root> switch -c tinker/learn-<yyyy-mm-dd>[-<focus>]`. Never
   commit a retro, checkpoint or anything under `.tinker/`.
4. **Edit and measure.** Apply the edits. When an edit changes behavior no live case
   covers, first add or tighten one `regression` case and run it on the base branch: it
   must fall short there, or it does not measure the edit. Never edit a `heldout` case
   to fit a change. Run the regression and held-out sets with the accepted baseline's
   arguments (with `--adaptive`, a case that falls short here or in the baseline runs
   twice more, so one unlucky run on either side does not decide the gate), then the
   gate; measure any case it lists under `Uneven runs` to the same count on both sides
   before trusting a verdict that case decides. A result with errored runs is invalid:
   rerun it. If the gate fails, undo your own edits, switch back, delete the branch with
   `git branch -d` and report why. Without the `claude` CLI, leave the edits uncommitted
   on the branch, report the gate `not-verified` and stop.
5. **Record.** Accept the result as the new baseline, then commit the edits with the
   baseline file. The message names the evidence for each edit in words another reader
   can check without the retros, and includes the gate table. Never push or merge: the
   user reviews and merges, then reinstalls Tinker into the apps if they use it there.

Learning never changes safety rules, authorization boundaries or delegation limits
without the user asking for that specific change.
