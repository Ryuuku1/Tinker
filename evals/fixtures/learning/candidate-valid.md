---
candidate_id: 5b0c7c2e-0000-4000-8000-000000000002
repository: the disposable fixture repository
component: app.py startup
created_date: 2026-09-25
last_validated_date: none
revision: fixture commit
confidence: verified
status: candidate
---

# Candidate: the app prints `ready on <port>` once it listens

## Claim / Procedure

Wait for the line `ready on <port>` on standard output before sending requests.

## Observed Symptom & Provenance

- Symptom or trigger that surfaced it: requests sent before startup were refused.
- Source file/symbol, command or primary URL: `app.py`, `main()`.
- Originating task or job reference: fixture.

## Verification Evidence

- Check: started `python app.py --port <free port>` and read one line: `ready on <port>`.

## Invalidation Conditions

- `main()` stops printing the readiness line or prints it before listening.

## Target Destination

- Chosen target and reason: `local-knowledge`; it helps every running-app check here.
