#!/usr/bin/env bash
# Tinker Flow, the conductor: no model and no Claude credential. The container sees only its own key volume.
set -euo pipefail
. /kit/forward.sh
BUZZ_PRIVATE_KEY=$(cat /agentkey/agent.sec); export BUZZ_PRIVATE_KEY
exec python3 /kit/flow.py
