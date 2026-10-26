#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo notes
mkdir -p product/notes/notes product/notes/tests
: > product/notes/notes/__init__.py
cat > product/notes/notes/messages_en.py <<'PY'
"""English messages for the notes app."""

MESSAGES = {
    "welcome": "Welcome back",
    "goodbye": "See you soon",
    "saved": "Note saved",
}
PY
cat > product/notes/notes/messages_pt.py <<'PY'
"""Portuguese messages, written by hand with the translator."""

MESSAGES = {
    "welcome": "Bem-vindo de volta",
    "holiday": "Boas festas",
}
PY
cat > product/notes/notes/holiday.py <<'PY'
"""The seasonal banner on the home screen."""
from notes.messages_pt import MESSAGES as PT


def banner(locale: str) -> str:
    return PT["holiday"] if locale == "pt" else "Happy holidays"
PY
cat > product/notes/tests/test_messages.py <<'PY'
import unittest

from notes.messages_en import MESSAGES


class MessagesTests(unittest.TestCase):
    def test_english_has_a_welcome(self):
        self.assertEqual(MESSAGES["welcome"], "Welcome back")
PY
commit_fixture notes
