# #reviews: read-only reviews by Tinker Reviewer

@mention **@Tinker Reviewer** with what to review. It cannot change anything: `/repo` and `/work` are
read-only for it, and its edit tools and the web are denied. It reads and runs read-only git commands;
it does not run tests.

## Say what to review

- A range or branch in the mounted repository: `/repo`, `master~3..master` or `master...feat/x`.
- One commit: `/repo`, `abc1234`.
- Work Tinker (the Lead) did in its clone: `/work/<topic>`, its uncommitted diff or its branch.

## Try

- `@Tinker Reviewer Review /repo master~1..master for bugs, security and missing tests.`
- `@Tinker Reviewer Review the uncommitted diff in /work/<topic>. Most severe first.`
- `@Tinker Reviewer Is integrations/buzz/kit/setup.ps1 safe to run twice? Evidence with file:line only.`

## You get

What it reviewed (folder and revision), then findings, most severe first, each with `file:line`, the
consequence and a failure scenario; or "no findings", with what it did not check.
