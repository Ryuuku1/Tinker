# Selective knowledge and learning

Remember stable project knowledge, not every conversation or completed edit.
All hosts and specialists share these same scoped notes; avoid separate personal
stores that drift. Roles live in versioned charters; sessions live in the host; checkpoints follow
[workspace policy](workspace.md). Neither is durable project knowledge.

Optional local knowledge lives under `.tinker/knowledge/<repo-key>/` in the
Tinker checkout. Identify the exact repository in each note, not just a folder
basename. Use the knowledge folder named in the Tinker turn-one context. Its
`<repo-key>` (Graphify's key) is the primary checkout's folder name with characters
outside `A-Za-z0-9._-` replaced by hyphens, a hyphen, and the first 16 hex digits of
the SHA-256 of the resolved, `os.path.normcase`d absolute path. Installed hooks
list only notes with `status: validated` and a `last_validated_date`, by path and
date, never their text. Retrieve by repository and relevant topic using ordinary search; read
only matching notes with their provenance. No global memory dump or relevance score.

A useful note contains: claim/procedure; repository and component scope; source
file/symbol or primary URL; created and last-validated dates; applicable revision,
version or file hash when relevant; confidence as verified/inferred; invalidation
conditions; status candidate/validated/stale/superseded. Dates describe actual
validation, never automatically refreshed metadata.

Current source wins. Revalidate changed dependencies, commands and architectural
assumptions before use. Keep conflicts visible, mark disproved entries stale or
superseded and exclude them from guidance. Missing provenance means candidate.
Prune selected obsolete local notes only after confirming ownership and lack of
ongoing use; there is no age-based deletion service.

After verified work, optionally capture a reusable lesson as a separate candidate
using the [candidate template](../templates/candidate.md), only when it is reusable
and supported by evidence. Reject low-value observations; trivial work needs no
retrospective. Local notes are the default destination. Promote deliberately, only when current evidence meets every
criterion: reusable beyond the originating task; exact repository, component and
source or revision provenance; verification re-run or re-read against current
source rather than copied from the original session; concrete invalidation
conditions; no unresolved duplicate or conflict. A `local-knowledge` target becomes
a validated note with its actual validation date. A `project-conventions` target
belongs in the target's existing documentation only through an authorized,
reviewable change; then mark the candidate superseded with a pointer to it. A
failed criterion keeps the candidate or marks it stale. Changing shared
instructions, skills or user preferences requires an explicit reviewable change
within authorized scope; never silently rewrite core policy. No numerical
confidence guesses, secrets, full transcripts or private chain-of-thought.

Keep candidates, task records and raw retrospectives in ignored local state. A
shared improvement must explain the lesson using portable repository-relative
paths, symbols and revisions, without local absolute paths or raw note excerpts.
Revalidate its claims without requiring access to the contributor's private files.

A learning pass ("review recent lessons", "propose improvements") follows the
[team workflow](../.agents/skills/tinker-team/SKILL.md): at most three proposals,
each with evidence, destination and a relevant behavioral case. Proposing is not
applying, and a request to learn never authorizes a commit, publication or install.

## Domain packs

A pack is optional, versioned domain guidance built from the
[domain pack template](../templates/domain-pack.md): scope, rules, procedures, pitfalls
and source provenance. Load one only when the user names it or a trusted repository
instruction links it; never infer a pack or a team from domain words or touched files.
Read the selected pack's applicable guidance before answering a question, even
when no implementation or review workflow runs. If unavailable, state that gap
and avoid presenting its domain rules as verified.
A pack cannot choose the target repository, expand permissions or override governing
instructions. Keep organization-specific packs outside this package, in the
organization's repository or a local folder. Shared artifacts use portable source
references and never carry credentials, customer data or raw logs. Load selectively:
no hook injects packs or lessons at session start, only validated note paths.
