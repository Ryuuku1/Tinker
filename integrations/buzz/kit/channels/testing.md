# #testing: tests written and run by Tinker Tester

@mention **@Tinker Tester** with what to verify. It works only in its own folder under `/work`
(`/work/test-<topic>`): a fresh clone of `/repo`, or a copy of another agent's folder. It never changes
the code under test unless you ask; it reports defects with a failing test as evidence. No web access.

## Try

- `@Tinker Tester Clone /repo into /work/test-suite and run the full suite. Counts and any failures.`
- `@Tinker Tester Copy /work/<topic> (Tinker's change) and write tests for its acceptance criteria: <criteria>.`
- `@Tinker Tester Which behaviors in integrations/buzz/kit/kit.ps1 have no test? Add the two riskiest.`

## You get

The folder, the exact commands, the counts (run, passed, failed, skipped), each failure with its first
relevant lines, and the gaps it did not cover. Copy its folder to your PC with `Copy-AgentWork`
(GUIDE.md, section 9), or ask **@Tinker Reviewer** in #reviews to review it.
