#!/usr/bin/env bash
# Builds the eval workspace (the run's cwd) as a Tinker root: the charter (AGENTS.md, policies, roles, templates,
# profiles, skills) copied from the snapshot scripts/eval_live.py took at run start, an empty .tinker/, and fixture
# git repositories under ./product/<name>. Source it from a case's setup.sh:
#   . "$(dirname "$0")/../_shared/workspace.sh"
# eval_live.py writes root.txt (the snapshot's path) next to this file in the rendered bundle; the checkout has none.
set -euo pipefail
shared_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$shared_dir/root.txt" ]; then
  echo "No $shared_dir/root.txt: run the live evals through scripts/eval_live.py." >&2
  exit 1
fi
tinker_root="$(head -n 1 "$shared_dir/root.txt")"
for item in AGENTS.md CLAUDE.md policies roles templates profiles .agents; do
  if [ -e "$tinker_root/$item" ]; then cp -R "$tinker_root/$item" .; fi
done
mkdir -p .tinker/tasks .tinker/retros product

# A fixture repository at product/<name> on branch <base> (default main).
new_repo() {
  mkdir -p "product/$1"
  git -C "product/$1" init -q
  git -C "product/$1" symbolic-ref HEAD "refs/heads/${2:-main}"
}

# Commit whatever the case put under product/<name> (call after writing fixture files).
commit_fixture() {
  git -C "product/$1" add -A
  git -C "product/$1" -c user.name=eval -c user.email=eval@example.invalid -c commit.gpgsign=false \
    commit -qm "${2:-fixture}"
}

# The shop fixture's own instructions, with an agent playbook (base branch develop, gate `make verify`).
shop_playbook() {
  cat > product/shop/AGENTS.md <<'MD'
# Shop

A small pricing library. Prices are integer cents.

## Agent playbook

- Base branch: develop
- Gates: Python change: `make verify` (ruff, then pytest on tests/); docs-only change: none.
- Deliverable and commits: one commit per change, Conventional Commits; never push.
- Worktrees: `git worktree add ../shop-<slug> -b <type>/<slug> origin/develop`.
- Live pass: none (a library with no UI or server).
- Graph: on-demand
- Pitfalls: money is integer cents, never float; keep input validation in the public functions.
MD
}

# The shop fixture: a pricing library with one test module, a Makefile gate and the playbook above, committed on
# develop. Cases add or change files afterwards and commit again.
shop_fixture() {
  new_repo shop develop
  mkdir -p product/shop/shop product/shop/tests
  shop_playbook
  cat > product/shop/pyproject.toml <<'TOML'
[project]
name = "shop"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []
TOML
  printf 'verify:\n\truff check .\n\tpython -m pytest tests -q\n' > product/shop/Makefile
  : > product/shop/shop/__init__.py
  cat > product/shop/shop/pricing.py <<'PY'
"""Prices are integer cents."""


def apply_discount(price_cents: int, percent: int) -> int:
    """Price after a percentage discount, rounded half up to the cent."""
    if price_cents < 0:
        raise ValueError("price_cents must not be negative")
    return (price_cents * (100 - percent) + 50) // 100
PY
  cat > product/shop/tests/test_pricing.py <<'PY'
import unittest

from shop.pricing import apply_discount


class ApplyDiscountTests(unittest.TestCase):
    def test_ten_percent_off(self):
        self.assertEqual(apply_discount(1000, 10), 900)

    def test_rejects_negative_price(self):
        with self.assertRaises(ValueError):
            apply_discount(-1, 10)
PY
  commit_fixture shop
}

# The catalog fixture's skeleton (no playbook): cases add the modules and tests, then commit_fixture catalog.
catalog_fixture() {
  new_repo catalog
  mkdir -p product/catalog/catalog product/catalog/tests
  cat > product/catalog/pyproject.toml <<'TOML'
[project]
name = "catalog"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []
TOML
  : > product/catalog/catalog/__init__.py
}
