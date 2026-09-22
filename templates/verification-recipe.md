# Verification recipe: <application, flow or change>

Copy into the job's task record under the Tinker checkout, never the product
repository, and fill it from trusted project guidance (README, scripts, task runners,
launch configurations) and actual observations. Follow the
[application verification reference](../policies/app-verification.md). Remove unused
lines; anything not established stays marked unknown.

## Checkout and prerequisites

- Repository, worktree and exact revision:
- Runtime and tool versions required, and how they were confirmed:

## Environment and external dependencies

- Configuration source (files, variables) and the values this run uses:
- Every external service the flow can reach, and whether it is stubbed, local or shared:
- Shared environments and production data this run must not touch, and how that is ensured:

## Startup and readiness

- Start command, working directory and the free port chosen:
- Readiness check and its time limit:

## Test identity and data

- Test-only accounts, tokens or fixtures (never real credentials):
- Data this run creates, and how it is identified:

## Flow and expected outcome

- The changed UI, API or CLI flow, step by step:
- The expected result of each step, including error or empty states that matter:

## Evidence and cleanup

- Evidence captured (responses, output, screenshots) and where it is stored:
- Resources this run started or created (process ids, containers, files, data) and how each was removed:
- Result: passed / failed / skipped / not-verified, with the reason:
