#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"

# A small store: a CSV importer into SQLite, a JSON API over it and a static web page, each with its own tests.
new_repo store
mkdir -p product/store/store product/store/tests product/store/web
cat > product/store/AGENTS.md <<'MD'
# Store

Orders are imported from the warehouse CSV export into SQLite, served as JSON and shown on static pages.
Money is integer cents.

## Agent playbook

- Base branch: main
- Gates: importer or API change: `python -m pytest tests -q`; web change: `node --test web/`; docs-only change: none.
- Deliverable and commits: one commit per change, Conventional Commits; never push.
- Worktrees: `git worktree add ../store-<slug> -b <type>/<slug> main`.
- Live pass: `python -m store.server`, then open http://localhost:8000/orders.html.
- Graph: on-demand
- Pitfalls: money is integer cents, never float; months are `yyyy-mm` in UTC.
MD
cat > product/store/pyproject.toml <<'TOML'
[project]
name = "store"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []
TOML
: > product/store/store/__init__.py
cat > product/store/store/importer.py <<'PY'
"""Imports the warehouse CSV export (id, sku, category, status, ordered_on, total_cents) into SQLite."""
import csv
import sqlite3

SCHEMA = """CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY, sku TEXT NOT NULL, category TEXT NOT NULL, status TEXT NOT NULL,
    ordered_on TEXT NOT NULL, total_cents INTEGER NOT NULL)"""


def import_orders(csv_path, db: sqlite3.Connection) -> int:
    db.execute(SCHEMA)
    with open(csv_path, newline="", encoding="utf-8") as handle:
        rows = [(r["id"], r["sku"], r["category"], r["status"], r["ordered_on"], int(r["total_cents"]))
                for r in csv.DictReader(handle)]
    db.executemany("INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?)", rows)
    db.commit()
    return len(rows)
PY
cat > product/store/store/api.py <<'PY'
"""JSON routes over the orders database."""
import re
import sqlite3

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def orders_for_month(db: sqlite3.Connection, month: str) -> tuple[int, object]:
    if not MONTH.match(month or ""):
        return 400, {"error": "month must be yyyy-mm"}
    rows = db.execute("SELECT id, sku, category, status, total_cents FROM orders WHERE ordered_on LIKE ? ORDER BY id",
                      (month + "-%",)).fetchall()
    return 200, [dict(zip(("id", "sku", "category", "status", "total_cents"), row)) for row in rows]


ROUTES = {"/api/orders": orders_for_month}
PY
cat > product/store/store/server.py <<'PY'
"""Serves web/ and the JSON routes on http://localhost:8000."""
import json
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from store.api import ROUTES

WEB = Path(__file__).resolve().parents[1] / "web"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def do_GET(self):
        url = urlparse(self.path)
        route = ROUTES.get(url.path)
        if route is None:
            return super().do_GET()
        with sqlite3.connect("store.db") as db:
            status, body = route(db, parse_qs(url.query).get("month", [""])[0])
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    ThreadingHTTPServer(("localhost", 8000), Handler).serve_forever()
PY
cat > product/store/tests/test_store.py <<'PY'
import sqlite3
import tempfile
import unittest
from pathlib import Path

from store.api import orders_for_month
from store.importer import import_orders

CSV = "id,sku,category,status,ordered_on,total_cents\nA1,MUG-1,kitchen,delivered,2026-03-02,1250\nA2,TEE-4,clothing,delivered,2026-04-01,1999\n"


class StoreTests(unittest.TestCase):
    def setUp(self):
        folder = Path(tempfile.mkdtemp())
        (folder / "orders.csv").write_text(CSV, encoding="utf-8")
        self.db = sqlite3.connect(":memory:")
        self.assertEqual(import_orders(folder / "orders.csv", self.db), 2)

    def test_orders_for_a_month(self):
        status, body = orders_for_month(self.db, "2026-03")
        self.assertEqual(status, 200)
        self.assertEqual([order["id"] for order in body], ["A1"])

    def test_rejects_a_bad_month(self):
        self.assertEqual(orders_for_month(self.db, "2026-3")[0], 400)
PY
cat > product/store/web/orders.html <<'HTML'
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Orders</title></head>
<body>
  <h1>Orders</h1>
  <input id="month" type="month">
  <table id="orders"><thead><tr><th>Order</th><th>Category</th><th>Status</th><th>Total</th></tr></thead><tbody></tbody></table>
  <script type="module" src="orders.js"></script>
</body>
</html>
HTML
cat > product/store/web/money.js <<'JS'
export function formatCents(cents) {
  return (cents / 100).toLocaleString("en", { style: "currency", currency: "EUR" });
}
JS
cat > product/store/web/orders.js <<'JS'
import { formatCents } from "./money.js";

export function rowsHtml(orders) {
  return orders.map((o) => `<tr><td>${o.id}</td><td>${o.category}</td><td>${o.status}</td><td>${formatCents(o.total_cents)}</td></tr>`).join("");
}

if (typeof document !== "undefined") {
  const month = document.getElementById("month");
  month.addEventListener("change", async () => {
    const response = await fetch(`/api/orders?month=${month.value}`);
    document.querySelector("#orders tbody").innerHTML = rowsHtml(await response.json());
  });
}
JS
cat > product/store/web/orders.test.js <<'JS'
import { test } from "node:test";
import assert from "node:assert/strict";
import { rowsHtml } from "./orders.js";

test("renders one row per order", () => {
  const html = rowsHtml([{ id: "A1", category: "kitchen", status: "delivered", total_cents: 1250 }]);
  assert.match(html, /<td>A1<\/td>/);
});
JS
commit_fixture store
