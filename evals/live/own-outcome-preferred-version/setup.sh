#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo garden
mkdir -p product/garden/docs
cat > product/garden/docs/intro.md <<'MD'
# Garden planner guide

The planner shows when, where and how much to water each bed. Start on the map: every bed opens its own schedule. Amounts follow the climate and soil you pick, so two neighbours can recieve different advice for the same week with neither of them being wrong.
MD
commit_fixture garden
