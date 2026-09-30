# #flows: a whole piece of work from one message, with Tinker Flow

Write your request in a new message, no @mention needed. Start it with a flow's name to choose the flow;
otherwise Tinker Flow suggests one and waits for you to reply `go`, or another flow's name, in the thread. It
runs the agents in order, in one thread under your message, and hands each one only what it needs: your request
and the earlier agents' reports, quoted as data. Tinker Flow has no AI of its own, so running a flow costs no
extra tokens; it obeys only you and cannot loop. In another channel, start with **@Tinker Flow** and answer it by
name there too (`@Tinker Flow go`, `@Tinker Flow stop`), since an untagged reply there goes to that channel's agent.

| Flow | Agents, in order | For |
|---|---|---|
| `story` | Planner → Tinker → Tester → Reviewer | a change: shaped, built test-first, verified, reviewed |
| `bug` | Tinker → Tester → Reviewer | a defect: root cause, fix with a regression test, verified, reviewed |
| `review` | Reviewer → Tester | a branch, commit or range: findings and a full test run |
| `research` | Researcher → Planner | a question: a sourced answer, then what it means for the code |

## Try

- `story Warn in setup.ps1 when Docker has less than 8 GB of disk free`
- `bug Get-KitStatus shows "no key yet" for an agent that has a key`
- `review /repos/Tinker master~3..master`
- `research Which Claude Code settings cut tokens for unattended agents?`
- `The login page crashes on Safari`: no flow named, so Tinker Flow suggests `bug` and waits for your `go`.
- `help` lists the flows; `stop` in a flow's thread stops it.

## You get

A ▶️ line with the plan, each agent's report in the thread as it finishes, and a ✅ line with the time and,
for story and bug, the folder to copy out with `Copy-AgentWork <topic>`. If a step fails, a ⏹️ line says
where and why, and nothing later runs.
