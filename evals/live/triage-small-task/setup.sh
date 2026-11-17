#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo tally
mkdir -p product/tally/tally
cat > product/tally/tally/count.py <<'PY'
def count_rows(rows):
    tmp = 0
    for row in rows:
        if row.strip():
            tmp += 1
    return tmp
PY
commit_fixture tally
