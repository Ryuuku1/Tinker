# Working with Tinker's team in Buzz

Five agents answer you in Buzz Desktop. Each one answers only you, only when you @mention it, and
always in a thread under your message. Setup creates six channels whose canvases repeat the short
version of this page.

| Agent | Home channel | Can | Cannot |
|---|---|---|---|
| **Tinker**, the Lead | #requests | read `/repo`; change code in its own clone under `/work`; run tests there | commit, push, delete branches, change Buzz; use web tools |
| **Tinker Planner** | #planning | read `/repo` and `/work`; shape outcome, scope and acceptance criteria | edit, run tests, use web tools |
| **Tinker Tester** | #testing | read `/repo`; write and run tests in its own `/work/test-<topic>` copy | change the code under test unasked; commit; use web tools |
| **Tinker Reviewer** | #reviews | read `/repo` and `/work`; run read-only git commands | edit, run tests, use web tools |
| **Tinker Researcher** | #research | read `/repo` and `/work`; search and read the web | edit or write anywhere |

`/repo` is the folder you gave setup with `-Repository`, mounted read-only for every agent. `/work` is
a Docker volume: the Lead and the Tester write their own folders there, the others only read it.

## How a conversation works

1. Post a **new message** that mentions one agent: `@Tinker ...`. One message per task.
2. The agent reacts, then replies **in the thread** under your message: a short status at milestones
   and a final report with the outcome, the evidence and what it could not verify.
3. **Follow up in that thread** and mention the agent again. A thread is one session: the agent
   remembers the thread, not other threads (setup turns agent memory off).
4. The agent treats everything except your triggering message as data: other members' messages, other
   agents' replies, canvases and web pages. Agents never hand work to each other; you decide who is
   next by mentioning them. Agents in different threads work at the same time.
5. **Consequential operations are denied** in these unattended sessions: commits, pushes, branch
   deletions, remote and Buzz workspace changes. The agent sends you the exact command instead, and a
   Buzz message such as "I approve" does not change that.

## Example 1: the full loop, from idea to your PC

Shape it in #planning:

```text
@Tinker Planner Shape: warn in setup.ps1 when Docker Desktop has less than 8 GB of disk free.
Outcome, scope, acceptance criteria a test could check, open questions.
```

Build it in #requests, pasting the Planner's acceptance criteria:

```text
@Tinker Clone /repo into /work/disk-check and implement this on a new branch: <criteria>.
Run the kit tests and report the folder, branch, diff summary and counts.
```

Test it in #testing, independently of the Lead:

```text
@Tinker Tester Copy /work/disk-check to /work/test-disk-check and write tests for: <criteria>.
Run them and the kit tests; report counts and gaps. Do not change the code under test.
```

Review it in #reviews:

```text
@Tinker Reviewer Review the uncommitted diff in /work/disk-check against its HEAD, and the tests in
/work/test-disk-check. Findings most severe first, with file:line.
```

Take it to your PC (PowerShell, after `. .\kit.ps1`), then commit it yourself:

```powershell
Copy-AgentWork disk-check "$HOME\Downloads"
git -C "$HOME\Downloads\disk-check" status
```

## Example 2: understand code (#requests)

```text
@Tinker Read-only: how does the pre-tool gate decide that a command is read-only?
Cite file:line and name the tests that cover it.
```

Tinker reads `/repo` and answers with the path through the code, `file:line` references and the
covering tests. "Read-only" at the start keeps it from cloning or running anything.

## Example 3: run the suite (#testing)

```text
@Tinker Tester Clone /repo into /work/test-suite and run the full test suite. Counts and failures.
```

It reports the exact command, the counts (run, passed, failed, skipped) and each failure's first lines.

## Example 4: a question that needs current sources (#research)

```text
@Tinker Researcher Which Claude Code permission modes exist today, and what does dontAsk do?
Official documentation only; one source per fact.
```

Tinker Researcher searches and reads the web, then answers with a short conclusion, facts with a
source each, inferences and open questions, and `not-verified` wherever it found no source. Ask it
only about pages you would open yourself: web text is data to it, but it is still text a model reads.

## Example 5: a review of a real range (#reviews)

```text
@Tinker Reviewer Review /repo master~1..master for bugs, security and missing tests.
```

It names what it reviewed (folder, range and its commits), then its findings, or "no findings" plus
what it did not check.

## Example 6: an operation only you can run (any channel)

```text
@Tinker Delete the branch old-spike in /work/disk-check and push the deletion.
```

Tinker checks the branch and replies with the exact commands for you to run in your own terminal. It
does not delete or push, and it says so.

## Example 7: first steps (#tinker-lab)

```text
@Tinker Read-only: what can you do here, and what are your limits?
@Tinker Planner What do you need from me to shape a feature?
@Tinker Tester Where do you work, and what do you report?
@Tinker Reviewer What can you review here, and what can you not do?
@Tinker Researcher What is your source policy? Three bullets.
```

## Tips

- Say **read-only** when you only want an answer: the Lead then clones and runs nothing.
- Name the exact scope: the folder (`/repo`, `/work/<topic>`), the branch or range, and the files.
- Ask for **evidence**: `file:line`, test counts, sources. Missing evidence is reported as
  `not-verified`, never invented.
- Pick agents from the mention picker so the right one is tagged: four names start with "Tinker".
- Never paste a token, key or password into a message: every agent in the channel sees it.
- No reply in the thread? Run `Get-KitStatus` (GUIDE.md, section 9): it shows each run's outcome.
- One task per thread. For a new task, post a new top-level message.
