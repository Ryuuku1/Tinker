# #requests: work with Tinker, the Lead

@mention **@Tinker** in a new message: one message per task. It answers only you, in the thread under
your message. Follow up in that thread and mention it again.

## What it does here

- Explains and plans from the repositories under `/repos`, which are read-only for every agent, and
  from the web when it needs current facts.
- Changes code only in its own clone under `/work`, runs the tests there, and reports the folder,
  branch, diff summary and test counts.
- Never commits, pushes, deletes branches or changes Buzz for you. It sends you the exact command to
  run yourself; "I approve" in Buzz does not change that.

## Try

- `@Tinker Read-only: how does the pre-tool gate decide that a command is read-only? Cite file:line.`
- `@Tinker Read-only: which tests cover the Buzz reply shape? One line each.`
- `@Tinker Plan, no changes yet: what would it take to <your feature>? Steps, files and risks.`
- `@Tinker Clone /repos/<name> into /work/<topic>, add a test for <behavior>, run the suite and report the counts.`

## Next

- The whole loop from one message: #flows (`@Tinker Flow story <request>`).
- Shape it first: #planning. Tests for the change: #testing. An independent review: #reviews. A fact
  check with sources: #research.
- Take the work to your PC: `Copy-AgentWork <topic> "$HOME\Downloads"` (GUIDE.md, section 10).
