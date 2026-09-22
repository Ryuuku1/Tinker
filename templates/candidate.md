---
candidate_id: <UUID>
repository: <exact repository identity, not a folder basename>
component: <module, directory or symbol scope>
created_date: <YYYY-MM-DD>
last_validated_date: <YYYY-MM-DD or none>
revision: <commit, version or file hash the claim applies to>
confidence: verified | inferred
status: candidate
---

# Candidate: <one-line claim>

Copy into the package's ignored `.tinker/knowledge/<repo-key>/` under
[knowledge policy](../policies/knowledge.md). Fill with actual observations and
remove guidance lines. Never save secrets, full transcripts or private reasoning.

## Claim / Procedure

The reusable fact or steps, precise enough to act on without this session.

## Observed Symptom & Provenance

- Symptom or trigger that surfaced it:
- Source file/symbol, command or primary URL:
- Originating task or job reference:

## Verification Evidence

- Check: exact command or inspected source, working directory, revision, exit
  status and concise result.
- Parts not verified, labeled inferred:

## Invalidation Conditions

- Changes that would make this wrong, such as a dependency upgrade, moved file or
  changed convention:

## Target Destination

- `local-knowledge`: validated note under `.tinker/knowledge/<repo-key>/`.
- `project-conventions`: the target's existing documentation, only through an
  authorized, reviewable change.
- Chosen target and reason:
- Promotion review: reviewer, date, criteria outcome and resulting note or change.
  Update `status` and `last_validated_date` only after that review.
