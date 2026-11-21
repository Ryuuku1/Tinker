# Evaluating Tinker

Two different claims:

1. Package checks: imports, references, native descriptors, skill layout and the
   gate's classifier are consistent. Run `python -m unittest discover -s tests -v`.
   They prove structure, not agent behavior.
2. Live Claude Code evals: the cases in [live](live/) run real Claude Code sessions
   through `claude plugin eval` and grade themselves; `scripts/eval_live.py gate`
   compares a result with the accepted baseline. The learn pass depends on this gate.
   They measure Claude Code only: Codex and Antigravity behavior is not verified.

Each case belongs to one set. Develop against `regression` cases. The `heldout` cases
are for acceptance only; never edit one to make a change pass.

## Live evals (Claude Code)

The cases in [live](live/) are behavioral evals the Claude Code host runs and grades
itself through `claude plugin eval`: each `live/<case>/case.yaml` holds the prompt,
allowed tools and graders (`file_exists`, `regex`, `tool_used`, and a few `llm`
judgements), and its `setup.sh` builds the workspace. Tags put each case in exactly
one set, `regression` or `heldout`.

Each workspace is a Tinker root built from the run's snapshot (charter, policies,
roles, templates, skills, an empty `.tinker/`) with tiny invented git repositories
under `product/<name>`, created by [live/_shared/workspace.sh](live/_shared/workspace.sh).
Eval runs do not load `CLAUDE.md`, so each case carries `AGENTS.md` as its appended
system prompt (the `TINKER_AGENTS_MD` placeholder, filled in per run).

```text
python scripts/eval_live.py run [--case GLOB] [--tag TAG ...] [--runs N] [--model M]
                                [-j N] [--ablation none|with-without] [--adaptive]
                                [--accepted FILE] [--force] [--percent-per-run F]
                                [--judge-model ID]
python scripts/eval_live.py gate --result evals/live/results/<runId>.json [--accept]
                                 [--min-paired N]
```

`run` copies the checkout's tracked and untracked-but-not-ignored files once into
`<temp>/tinker_eval_<runId>/tinker` (never `.tinker/` or other ignored files), renders
the Claude plugin bundle from that copy without hooks, and runs the cases there, so
edits made during a run never reach it; the run folder stays behind as the record of
what was measured. Defaults: `--model opus`, 4 runs at once, one run per case unless
the case sets `runs:`, `--ablation none` (`with-without` adds a no-plugin arm and
doubles the runs). It prints the result path and copies the JSON to the ignored
`evals/live/results/<runId>.json`. Its exit code is `claude plugin eval`'s (1 when a
case scores below 1.0). `llm` graders are judged by one pinned model, `--judge-model`
(default `claude-haiku-5-5`, an exact id: the CLI's `haiku` alias moves with each
release, and a new judge scores the same answers differently). The result records it as
`suite.judgeModel`.

`--adaptive` then runs each case that fell short of 1.0 twice more, whether it fell
short in this run or in the accepted baseline, and merges those runs into the result,
which records `adaptive` and `mergedFrom`.
- The baseline's per-case means count only when it was measured with the same model,
  the same judge and `--adaptive`. `--accepted` names another baseline file.
- Only the plugin arm re-runs.
- A case with an errored run is left as it is, since the result is invalid anyway.
- A case that already has three runs is not re-run.
- A case that fell short here but has fewer runs in the baseline runs again at the
  baseline's own commit until the counts match. Usually that is a baseline case perfect
  in its one run. The runs are recorded under `baselineTopUp`, for `gate` to pool.
- A set too small for a paired verdict (fewer than 8 baseline cases, such as heldout)
  whose cost per run passes the baseline's by more than 10% gets the same: each of its
  cases runs twice more here and again at the baseline's commit, so one costly draw on
  either side does not decide the cost verdict. It applies only when the run covers
  every baseline case of that set.
- The baseline's commit is found by the `tree` fingerprint the baseline recorded: a hash
  of the measured files, leaving out `accepted.json`, results and bytecode caches. The
  runner tries HEAD, then the last ten commits that changed `accepted.json`. With no
  match the baseline keeps its runs, and `gate` lists the case as uneven.

One unlucky run then costs a case a third of its score instead of all of it, while a
real regression still fails three times. Both sides of the comparison end with the same
number of runs for every case that fell short on either.

`gate` scores the plugin arm per set against `evals/live/accepted.json`: each case's
mean score and mean cost per run, averaged over the set's cases (a case run three times
weighs what a case run once does). It passes (exit 0) when each set's score is at least
the accepted one minus 0.02 and its cost per run at most 10% higher
(`--score-tolerance`, `--cost-tolerance`); otherwise it fails (exit 1).
- **Paired cases:** when a set shares at least eight cases with the baseline
  (`--min-paired`) whose `case.yaml` is unchanged, the verdict compares those cases one
  by one instead: it fails on score only when the 95% upper bound of the mean change is
  below zero and the mean change is below minus half the score tolerance, and on cost
  only when the 95% lower bound of the mean cost change is above zero and the change
  exceeds the cost tolerance. One flaky case moves a set mean by a whole step but stays
  inside that bound; a small slide across every case does not. The gate prints each
  set's paired change with its bound, and names cases that dropped by 0.5 or more so
  their graders get checked.
- **New or changed cases:** a case missing from the baseline, or whose `case.yaml` hash
  differs from the one recorded, is listed and left out of the paired verdict: its old
  mean measured another prompt or grader.
- **Errored runs:** a result with errored or unstarted runs is invalid (exit 2) and
  cannot be accepted.
- **Another model, judge or mode:** a result from another model, another judge or
  another adaptive mode than the baseline never passes, since each moves scores without
  any edit. It can only be accepted, which replaces the baseline. A baseline that names
  no judge was graded by the CLI's `haiku` alias.
- **Pooled baseline runs:** the gate pools a result's `baselineTopUp` runs into that
  case's baseline mean, and moves the set's mean by the change. It prints which cases it
  pooled.
- **Uneven runs:** the gate lists a case that still fell short on one side and ran a
  different number of times on each, such as one whose baseline commit was not found.
  Its mean over fewer runs is the weaker estimate, so measure it to the same count
  before trusting a verdict it decides.
- **Accepting:** `--accept` records model, judge, adaptive mode, commit, the measured
  tree's fingerprint, the per-set and per-case score, cost per run and run count, and
  each case's `case.yaml` hash. It keeps
  the sets and cases the result did not cover. Commit `accepted.json` with the change it
  measured, so the commit that holds it also holds the measured tree.

Without a baseline, `gate` reports `no baseline` and only `--accept` succeeds. The first
baseline is the user's call, from a full, reviewed run (`run --adaptive` with no
filter, then `gate --accept`); it was recorded at `c3f20ef`. Keep `--adaptive` when
learn passes measure against it: the gate compares like with like.

Writing cases: a case meant to measure a change must fall short on the base branch
before the change (red first); one that passes there too is only a regression guard,
worth its runs for behavior a later edit could break. Grade a fact the answer must
state with a `regex` grader and keep an `llm` judge to one or two facts. A judge that
fails answers meeting every clause is noise: replace it with discriminating patterns,
checked offline against the grader evidence stored in past results. A case that edits
code can outlast the 300-second default; give it `timeout_seconds: 600` under
`execution`.

Cost and usage: every agent run is a full Claude session on your own account, sharing
one rate limit. A call that starts more than 20 agent runs first reads the five-hour
window with one Haiku turn and refuses when the runs (assumed `--percent-per-run`, 0.4%
of the window each; measured Opus runs used about 0.2-0.6%) will not fit; it also
refuses when the usage cannot be read. `--adaptive` checks again before more than 20
re-runs.
`--force` skips the check. A run that hits the usage limit still costs what it spent
and is invalid. Narrow a run with `--case`, `--tag` or `--runs 1` while iterating.

Requirements and limits: `claude` and `git` on PATH, and bash for the scaffolds (on
Windows Git Bash, which the runner puts first on PATH; WSL's `bash` cannot run them).
On Windows the eval runner cannot sandbox shell tools, so cases allow only Read, Grep,
Glob, Write, Edit, Skill and Agent, and prompts state that shell commands are
unavailable. Behavior that needs a shell (running gates, fetching, rebasing) is graded
by what the agent plans and reports, not by executing it. The package tests in
`tests/test_eval_live.py` use a fake `claude` and build every scaffold; they never run
a model.
