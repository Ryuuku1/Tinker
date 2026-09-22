# Verifying a running application

Use when a change affects a UI, API or CLI flow that automated tests do not fully show
and the request or its risk warrants running it. Automated checks come first.

1. Discover trusted project guidance first: README, scripts, task runners, launch
   configurations and existing recipes. Propose new configuration only when none
   exists, as a reviewable change. Record the flow in a
   [verification recipe](../templates/verification-recipe.md) when it helps reuse.
2. Establish isolation. A localhost address alone proves nothing: inspect configuration
   and environment for calls to shared or production services and data, and use the
   project's stubs or local equivalents. If isolation cannot be established, do not run
   it; report `not-verified` with the reason.
3. Start only what the flow needs, on a free port, with test identities and data. Never
   force-kill a port's owner or stop a process this run did not start: choose another
   port or report the check blocked.
4. Exercise the changed flow with the tools actually available (HTTP client, command
   line, a browser tool if present); no particular plugin is required. Capture actual
   responses, output or screenshots. Store evidence with the task record under the
   Tinker checkout, never in the product repository.
5. Clean up exactly what this run created: its processes, containers, files and data.
   Report anything that could not be removed.

Report each running check as `passed`, `failed`, `skipped` or `not-verified`, with the
reason. A missing capability never erases automated checks that passed, and it stays
visible in the answer. Review keeps its read-only scope: rely on existing evidence or
report the running check `not-verified`; start, seed or change nothing.
