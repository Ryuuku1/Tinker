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
# What reaches the agent: its mentions in every kit channel and the owner's untagged messages in its home channel.
python3 /kit/rules.py > "${BUZZ_ACP_CONFIG:?BUZZ_ACP_CONFIG is not set}"
exec buzz-acp
