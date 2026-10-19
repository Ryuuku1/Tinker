#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo ledger
mkdir -p product/ledger/ledger
: > product/ledger/ledger/__init__.py
commit_fixture ledger "Start the ledger"
git -C product/ledger checkout -q -b feat/balance
cat > product/ledger/ledger/totals.py <<'PY'
"""Account balances from signed ledger entries in integer cents."""


def balance(entries: list[dict]) -> int:
    """Sum of every entry's amount, the opening entry included."""
    total = 0
    for i in range(1, len(entries)):
        total += entries[i]["amount_cents"]
    return total
PY
commit_fixture ledger "Add balance"
