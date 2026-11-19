#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo profiles
mkdir -p product/profiles/profiles product/profiles/tests
cat > product/profiles/pyproject.toml <<'TOML'
[project]
name = "profiles"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []
TOML
: > product/profiles/profiles/__init__.py
cat > product/profiles/profiles/settings.py <<'PY'
"""Settings the profile service reads at start-up."""

AVATAR_MAX_BYTES = 2_000_000
AVATAR_HOSTS = ("images.example.com", "cdn.example.com")
PY
cat > product/profiles/profiles/avatars.py <<'PY'
"""Profile pictures."""

from .settings import AVATAR_MAX_BYTES


def check_size(data: bytes) -> bytes:
    """Uploaded avatars stay under the size limit."""
    if len(data) > AVATAR_MAX_BYTES:
        raise ValueError("avatar is too large")
    return data
PY
cat > product/profiles/tests/test_avatars.py <<'PY'
import unittest

from profiles.avatars import check_size


class CheckSizeTests(unittest.TestCase):
    def test_rejects_oversized_avatar(self):
        with self.assertRaises(ValueError):
            check_size(b"x" * 2_000_001)
PY
commit_fixture profiles
