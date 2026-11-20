# Retro

The implement, investigate, review and shape workflows end with a retro: local
evidence for the [learn pass](learning.md#learn). A question answered without edits or
investigation needs none.

1. Save its lines first to the Tinker root's ignored
   `.tinker/retros/<yyyy-mm-dd>-<ticket or 2-4 word slug>-<workflow>.md` (add `-2`, `-3`
   when taken). That is the root this session names, never the folder an installed copy
   of this policy was read from. Use front matter `date`, `workflow`, `repository`
   (the folder name), `ticket` when there is one and, for implement and investigate,
   `round`: 1 for a first delivery, 2, 3 and so on when the user or a reviewer sent the
   work back. Say so when the session cannot write files.
2. Then close the final message with the same lines under `Retro`, at most five, and
   nothing after them:
   - What cost time or went wrong, if anything (at most two lines).
   - Optionally one proposed delta edit: add or change one bullet, never rewrite a
     section, naming its destination: a Tinker skill, policy, role or template; the
     target repository's `## Agent playbook` section
     ([template](../templates/agent-playbook.md)); or a local knowledge candidate. Do
     not apply it now.

Retros never leave this machine, but learn cites them in shared commits: no secrets,
credentials, personal or customer data, log or database excerpts, absolute paths or
task-record paths. Cite repository-relative paths, symbols, commands and ticket ids.
