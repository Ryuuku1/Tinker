#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
catalog_fixture
cat > product/catalog/catalog/text.py <<'PY'
"""Text helpers shared by the catalog's pages, feeds and exports."""
import re
import unicodedata


def slugify(text: str) -> str:
    """URL slug: ASCII, lower case, words joined by single hyphens ("Creme Brulee!" -> "creme-brulee")."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
PY
cat > product/catalog/catalog/export.py <<'PY'
"""CSV-ready rows for the partner export."""


def export_rows(products):
    return [{"sku": p["sku"], "name": p["name"], "price_cents": p["price_cents"]} for p in products]
PY
cat > product/catalog/tests/test_export.py <<'PY'
import unittest

from catalog.export import export_rows


class ExportRowsTests(unittest.TestCase):
    def test_keeps_sku_name_and_price(self):
        rows = export_rows([{"sku": "A1", "name": "Tea", "price_cents": 250}])
        self.assertEqual(rows[0]["sku"], "A1")
PY
commit_fixture catalog
