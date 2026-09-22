---
candidate_id: 5b0c7c2e-0000-4000-8000-000000000003
repository: the disposable fixture repository
component: app.py greeting
created_date: 2026-09-01
last_validated_date: none
revision: app.py sha256 0000000000000000000000000000000000000000000000000000000000000000
confidence: verified
status: candidate
---

# Candidate: `/greeting` returns plain text

## Claim / Procedure

`GET /greeting` answers with a plain-text body.

## Observed Symptom & Provenance

- Source file/symbol, command or primary URL: `app.py`, `Handler.do_GET`, at the revision above.

## Verification Evidence

- Check: read `Handler.do_GET` at the recorded revision.

## Invalidation Conditions

- `app.py` changes; the current file no longer has the recorded hash.

## Target Destination

- Chosen target and reason: `local-knowledge`.
