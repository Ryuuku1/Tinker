#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
catalog_fixture
cat > product/catalog/catalog/importer.py <<'PY'
"""Rows of the supplier CSV, validated and typed."""


def parse_row(row: dict) -> dict:
    sku = (row.get("sku") or "").strip()
    if not sku:
        raise ValueError("sku is required")
    try:
        price_cents = int(row["price_cents"])
    except (KeyError, ValueError):
        raise ValueError("price_cents must be an integer") from None
    if price_cents < 0:
        raise ValueError("price_cents must not be negative")
    return {"sku": sku, "price_cents": price_cents}
PY
cat > product/catalog/tests/test_importer.py <<'PY'
import unittest

from catalog.importer import parse_row


class ParseRowTests(unittest.TestCase):
    def test_requires_sku(self):
        with self.assertRaises(ValueError):
            parse_row({"sku": " ", "price_cents": "100"})

    def test_types_price(self):
        self.assertEqual(parse_row({"sku": "A1", "price_cents": "100"})["price_cents"], 100)
PY
commit_fixture catalog
