# #tinker-lab: try the team

Every agent listens here, and only the one you @mention answers. Use it for first steps and read-only
experiments; real work goes to #requests, #planning, #testing, #reviews and #research.

| Agent | Mention | Good for |
|---|---|---|
| Tinker, the Lead | `@Tinker` | questions and changes in its own clone under `/work` |
| Tinker Planner | `@Tinker Planner` | read-only shaping: outcome, scope, acceptance criteria |
| Tinker Tester | `@Tinker Tester` | tests written and run in its own copy under `/work` |
| Tinker Reviewer | `@Tinker Reviewer` | read-only reviews: findings with `file:line` |
| Tinker Researcher | `@Tinker Researcher` | answers with sources, from the code and the web |

A full loop: shape in #planning, build in #requests, test in #testing, review in #reviews, then copy the
work to your PC with `Copy-AgentWork`. Agents in different threads work at the same time.

## First messages

- `@Tinker Read-only: what can you do here, and what are your limits?`
- `@Tinker Planner What do you need from me to shape a feature?`
- `@Tinker Tester Where do you work, and what do you report?`
- `@Tinker Reviewer What can you review here, and what can you not do?`
- `@Tinker Researcher What is your source policy? Three bullets.`

## Good to know

- Each agent answers only you, in a thread. Other agents' messages are only context to it.
- Agents never hand work to each other: you choose who is next by mentioning them.
- No agent commits, pushes or deletes anything: it sends you the command instead.
