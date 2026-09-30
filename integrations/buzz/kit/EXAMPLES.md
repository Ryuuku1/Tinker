# Working with Tinker's team in Buzz

Five agents and a conductor answer you in Buzz Desktop. Each agent answers only you: whatever you write in its
home channel, with no @mention needed, and wherever else you @mention it, always in a thread under your message.
Tinker Flow runs several of them in one thread for the request you write in #flows. Setup creates seven channels
whose canvases repeat the short version of this page. The examples below leave out the mention wherever the
channel makes it optional.

| Agent | Home channel | Can | Cannot |
|---|---|---|---|
| **Tinker**, the Lead | #requests | read `/repos`; change code in its own clone under `/work`; run tests there | commit, push, delete branches, change Buzz |
| **Tinker Planner** | #planning | read `/repos` and `/work`; shape outcome, scope and acceptance criteria | edit, run tests |
| **Tinker Tester** | #testing | read `/repos`; write and run tests in its own `/work/test-<topic>` copy | change the code under test unasked; commit |
| **Tinker Reviewer** | #reviews | read `/repos` and `/work`; run read-only git commands | edit, run tests |
| **Tinker Researcher** | #research | read `/repos` and `/work`; research in depth with sources | edit or write anywhere |
| **Tinker Flow** | #flows | run `story`, `bug`, `review` and `research` flows across the agents | think: it has no AI and only relays |

Every agent may search and read the web. `/repos/<name>` are the folders you gave setup, mounted read-only for
every agent. `/work` is a Docker volume: the Lead and the Tester write their own folders there, the others only
read it.

## How a conversation works

1. Post a **new message** in the agent's home channel (#requests for Tinker), with no mention needed, or
   mention it anywhere else: `@Tinker ...`. A message that mentions another agent goes only to that agent.
   One message per task.
2. The agent reacts, then replies **in the thread** under your message: a short status at milestones
   and a final report with the outcome, the evidence and what it could not verify.
3. **Follow up in that thread**: in the agent's own channel, just reply in its thread. Elsewhere, and in
   another agent's thread there, mention it again, or turn on **Automatically mention agents** in Buzz
   Desktop's mention picker so your thread replies keep it addressed. A thread is one session: the agent remembers the thread, not other threads (setup turns agent
   memory off).
4. The agent treats everything except your triggering message as data: other members' messages, other
   agents' replies, canvases and web pages. Agents never hand work to each other on their own; you decide
   who is next, or a flow does. Agents in different threads work at the same time.
5. **Consequential operations are denied** in these unattended sessions: commits, pushes, branch
   deletions, remote and Buzz workspace changes. The agent sends you the exact command instead, and a
   Buzz message such as "I approve" does not change that.

## Example 1: the whole loop from one message (#flows)

```text
story Warn in setup.ps1 when Docker has less than 8 GB of disk free
```

Tinker Flow answers with a ▶️ line (Planner → Tinker → Tester → Reviewer), then runs them one after
another in the thread. The Planner's brief goes to Tinker, who builds it test-first in
`/work/warn-in-setup-ps1-when-docker-has-less`. The Tester verifies it in its own copy, and the Reviewer
reviews both. A ✅ line ends it; take the work to your PC and commit it yourself (PowerShell, after
`. .\kit.ps1`):

```powershell
Copy-AgentWork warn-in-setup-ps1-when-docker-has-less "$HOME\Downloads"
git -C "$HOME\Downloads\warn-in-setup-ps1-when-docker-has-less" status
```

Other flows: `bug <what is wrong>`, `review /repos/<name> master~3..master`, `research <question>`. Without a
flow's name, Tinker Flow suggests one and waits for you to reply `go`, or another flow's name, in the thread.
Replying `stop` in the thread stops a flow after the current step. In any other channel, start with
`@Tinker Flow`, for example `@Tinker Flow story <request>`, and answer it by name there too:
`@Tinker Flow go`, `@Tinker Flow stop`.

## Example 2: the same loop step by step

Shape it in #planning:

```text
Shape: warn in setup.ps1 when Docker Desktop has less than 8 GB of disk free.
Outcome, scope, acceptance criteria a test could check, open questions.
```

Build it in #requests, pasting the Planner's acceptance criteria:

```text
Clone /repos/<name> into /work/disk-check and implement this on a new branch: <criteria>.
Run the kit tests and report the folder, branch, diff summary and counts.
```

Test it in #testing, and review it in #reviews:

```text
Copy /work/disk-check to /work/test-disk-check and write tests for: <criteria>.
Run them and the kit tests; report counts and gaps. Do not change the code under test.

Review the uncommitted diff in /work/disk-check against its HEAD, and the tests in
/work/test-disk-check. Findings most severe first, with file:line.
```

## Example 3: understand code (#requests)

```text
Read-only: how does the pre-tool gate decide that a command is read-only?
Cite file:line and name the tests that cover it.
```

Tinker reads `/repos` and answers with the path through the code, `file:line` references and the
covering tests. "Read-only" at the start keeps it from cloning or running anything.

## Example 4: run the suite (#testing)

```text
Clone /repos/<name> into /work/test-suite and run the full test suite. Counts and failures.
```

It reports the exact command, the counts (run, passed, failed, skipped) and each failure's first lines.

## Example 5: a question that needs current sources (#research)

```text
Which Claude Code permission modes exist today, and what does dontAsk do?
Official documentation only; one source per fact.
```

A short conclusion, facts with a source each, inferences and open questions, and `not-verified` wherever
it found no source. Ask about pages you would open yourself: web text is data to every agent, but it is
still text a model reads.

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
@Tinker Flow help
```

## Example 8: a diagram (#requests)

```text
@Tinker Draw an archify architecture diagram of /repos/<name>/<folder>, backed by the code, in
/work/diagram-<topic>. Report the finalize result.
```

Tinker writes the diagram's JSON, runs archify's `finalize` (validation, with every cited source checked
against the committed code in `/repos/<name>`; provenance; a check in Chromium) and replies with the folder
and each gate's result. Then, on your PC:

```powershell
Copy-AgentWork diagram-<topic> "$HOME\Downloads"
```

Open the `.html` file in that folder in your browser. It works offline and has export and dark mode.

## Tips

- Say **read-only** when you only want an answer: the Lead then clones and runs nothing.
- Name the exact scope: the folder (`/repos/<name>`, `/work/<topic>`), the branch or range, and the files.
- Ask for **evidence**: `file:line`, test counts, sources. Missing evidence is reported as
  `not-verified`, never invented.
- In an agent's own channel, and in #flows, you need no mention at all. Elsewhere, pick agents from the
  mention picker so the right one is tagged: five names start with "Tinker".
- In an agent's own channel every message of yours goes to that agent, replies in a flow's thread included,
  so run flows in #flows.
- Never paste a token, key or password into a message: every agent in the channel sees it.
- No reply in the thread? Run `Get-KitStatus` (GUIDE.md, section 10): it shows each run's outcome.
  `Get-KitUsage` shows the tokens each agent used.
- One task per thread. For a new task, post a new top-level message.
