# #reviews: read-only reviews by Tinker Reviewer

Write what to review here. This is Tinker Reviewer's own channel, so no @mention is needed (elsewhere,
@mention **@Tinker Reviewer**). It cannot change anything: `/repos` and `/work` are read-only for it and its
edit tools are denied. It reads, runs read-only git commands and checks documentation on the web; it does not
run tests.

## Say what to review

- A range or branch in a repository: `/repos/<name>`, `master~3..master` or `master...feat/x`.
- One commit: `/repos/<name>`, `abc1234`.
- Work Tinker (the Lead) did in its clone: `/work/<topic>`, its uncommitted diff or its branch.

## Try

- `Review /repos/<name> master~1..master for bugs, security and missing tests.`
- `Review the uncommitted diff in /work/<topic>. Most severe first.`
- `Is integrations/buzz/kit/setup.ps1 safe to run twice? Evidence with file:line only.`

## You get

What it reviewed (folder and revision), then findings, most severe first, each with `file:line`, the
consequence and a failure scenario; or "no findings", with what it did not check. For a review plus a
full test run, use `review <range>` in #flows.
