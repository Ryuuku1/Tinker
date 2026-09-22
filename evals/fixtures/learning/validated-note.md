---
candidate_id: 5b0c7c2e-0000-4000-8000-000000000001
repository: the disposable fixture repository
component: build
created_date: 2026-09-20
last_validated_date: 2026-09-20
revision: fixture commit
confidence: verified
status: validated
---

# Validated: unit tests run with `python -m unittest -v`

## Claim / Procedure

Run the fixture's unit tests from the repository root with `python -m unittest -v`.

## Verification Evidence

- Check: `python -m unittest -v` in the repository root, exit 0, one test run.

## Invalidation Conditions

- The tests move out of the repository root or adopt another runner.
