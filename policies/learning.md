# Eval-gated learning

The learn pass turns [retros](retro.md) and eval results into at most three small
edits to Tinker's instructions, kept only when the live evaluation gate passes.
Knowledge notes and candidates stay under the [knowledge policy](knowledge.md).
A lessons review ("review recent lessons", "propose improvements") runs step 1 only
and stops: each proposal names its evidence, destination and the live case that
would show it works. Proposing is not applying.

## Learn

A request such as "learn", "learn from recent work" or the front door's `learn [focus]`
authorizes steps 1-5 below, including the commit in step 5; nothing more. The live gate
needs the `claude` CLI; see the [evaluation guide](../evals/README.md).

1. **Evidence.** [Retros](retro.md) dated in the last 30 days (newest first, filtered by
   the focus when given), open items of recent checkpoints under `.tinker/tasks/`, and
   failing graders in the newest result under `evals/live/results/`. Pick at most three delta edits, each tied to its
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
   to fit a change. First run each case the edits touch once (`run --case <name> --runs 1`);
   fix or drop an edit whose case is red before paying for the full gate. Then run the
   regression and held-out sets with the accepted baseline's arguments, then the gate.
   When a set shares at least eight unchanged cases with the baseline, the gate compares
   them case by case with a 95% bound, so one flaky case does not fail it while a broad
   slide does; new or changed cases are listed, not gated. Graders are judged by one
   pinned model: a result judged by another only becomes a new baseline (`--accept`),
   after the user confirms that run's cost. With `--adaptive`, a case that falls short on either side
   ends with the same number of runs on both, measuring the baseline again at its own
   commit when needed, so one unlucky run does not decide the gate. Measure any case the
   gate still lists under `Uneven runs` to the same count on both sides before trusting
   a verdict that case decides. A result with errored runs is invalid: rerun it. If the
   gate fails, undo your own edits, switch back, delete the branch with `git branch -d`
   and report why. Without the `claude` CLI, leave the edits uncommitted on the branch,
   report the gate `not-verified` and stop.
5. **Record.** Accept the result as the new baseline, then commit the edits with the
   baseline file. The message names the evidence for each edit in words another reader
   can check without the retros, and includes the gate table. Never push or merge: the
   user reviews and merges, then reinstalls Tinker into the apps if they use it there.

Learning never changes safety rules, authorization boundaries or delegation limits
without the user asking for that specific change.
