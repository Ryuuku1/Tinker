#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
shop_fixture
cat > product/shop/shop/money.py <<'PY'
"""Amounts typed by customers, as integer cents."""


def parse_amount(text: str) -> int:
    """'12.50' -> 1250."""
    whole, _, fraction = text.strip().partition(".")
    if not whole.isdigit() or (fraction and not fraction.isdigit()) or len(fraction) > 2:
        raise ValueError(f"not an amount: {text!r}")
    return int(whole) * 100 + int(fraction or 0)
PY
cat > product/shop/tests/test_money.py <<'PY'
import unittest

from shop.money import parse_amount


class ParseAmountTests(unittest.TestCase):
    def test_two_decimals(self):
        self.assertEqual(parse_amount("12.50"), 1250)

    def test_rejects_text(self):
        with self.assertRaises(ValueError):
            parse_amount("twelve")
PY
commit_fixture shop "Add amount parsing"
