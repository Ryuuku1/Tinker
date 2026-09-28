# #requests: work with Tinker, the Lead

@mention **@Tinker** in a new message: one message per task. It answers only you, in the thread under
your message. Follow up in that thread and mention it again.

## What it does here

- Explains and plans from the repository mounted at `/repo`, which is read-only for every agent.
- Changes code only in its own clone under `/work`, runs the tests there, and reports the folder,
  branch, diff summary and test counts.
- Never commits, pushes, deletes branches or changes Buzz for you. It sends you the exact command to
  run yourself; "I approve" in Buzz does not change that.

## Try

- `@Tinker Read-only: how does the pre-tool gate decide that a command is read-only? Cite file:line.`
- `@Tinker Read-only: which tests cover the Buzz reply shape? One line each.`
- `@Tinker Plan, no changes yet: what would it take to <your feature>? Steps, files and risks.`
- `@Tinker Clone /repo into /work/<topic>, add a test for <behavior>, run the suite and report the counts.`

## Next

- Shape it first: #planning. Tests for the change: #testing. An independent review: #reviews. A fact
  check with sources: #research.
- Take the work to your PC: `Copy-AgentWork <topic> "$HOME\Downloads"` (GUIDE.md, section 9).
- No reply? `Get-KitStatus` shows each run's outcome (GUIDE.md, section 9).
