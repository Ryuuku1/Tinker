#!/usr/bin/env bash
# One Tinker agent (KIT_ROLE: lead, planner, tester, reviewer or researcher): buzz-acp with the agent's own key and
# its role's deny rules. The container sees only its own key volume.
set -euo pipefail
: "${KIT_ROLE:?KIT_ROLE is not set}"
python3 /opt/kit/deny.py "$HOME/.claude/settings.json" "$KIT_ROLE"
# The repositories under /repos are owned by the host user: trust each one by its exact path, nothing wider.
for d in /repos/*/; do if [ -d "$d" ]; then git config --global --add safe.directory "${d%/}"; fi; done
. /kit/forward.sh
BUZZ_PRIVATE_KEY=$(cat /agentkey/agent.sec); export BUZZ_PRIVATE_KEY
exec buzz-acp
