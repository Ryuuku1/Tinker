#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo members
mkdir -p product/members/members product/members/tests
: > product/members/members/__init__.py
cat > product/members/members/expiry.py <<'PY'
"""Single source of truth for card and pass expiry."""
from datetime import date


def is_expired(expires_on: date, today: date) -> bool:
    return expires_on < today
PY
cat > product/members/members/gate.py <<'PY'
"""Turnstile decisions."""
from datetime import date

from members.expiry import is_expired


def may_enter(card: dict, today: date) -> bool:
    return card["active"] and not is_expired(card["expires_on"], today)
PY
cat > product/members/tests/test_expiry.py <<'PY'
import unittest
from datetime import date

from members.expiry import is_expired


class IsExpiredTests(unittest.TestCase):
    def test_yesterday_is_expired(self):
        self.assertTrue(is_expired(date(2026, 1, 9), date(2026, 1, 10)))
PY
commit_fixture members
