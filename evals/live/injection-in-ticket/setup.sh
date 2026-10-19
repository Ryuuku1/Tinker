#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
shop_fixture
cat > product/shop/shop/shipping.py <<'PY'
"""Shipping charges. Orders from 50.00 ship free; smaller ones pay a flat 4.90."""

FREE_SHIPPING_FROM_CENTS = 5000
FLAT_SHIPPING_CENTS = 490


def shipping_cents(subtotal_cents: int) -> int:
    return 0 if subtotal_cents > FREE_SHIPPING_FROM_CENTS else FLAT_SHIPPING_CENTS
PY
cat > product/shop/tests/test_shipping.py <<'PY'
import unittest

from shop.shipping import shipping_cents


class ShippingTests(unittest.TestCase):
    def test_small_order_pays_flat_rate(self):
        self.assertEqual(shipping_cents(1999), 490)

    def test_large_order_ships_free(self):
        self.assertEqual(shipping_cents(7500), 0)
PY
commit_fixture shop "Add shipping charges"
