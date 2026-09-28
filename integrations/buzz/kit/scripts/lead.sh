#!/usr/bin/env bash
# The Lead: buzz-acp with the agent key. The container sees only its own key volume.
set -euo pipefail
. /kit/forward.sh
BUZZ_PRIVATE_KEY=$(cat /agentkey/agent.sec); export BUZZ_PRIVATE_KEY
exec buzz-acp
