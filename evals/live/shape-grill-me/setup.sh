#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo notes
mkdir -p product/notes/notes
: > product/notes/notes/__init__.py
cat > product/notes/README.md <<'MD'
# notes

A personal command-line notebook: `python -m notes add "text"`, `python -m notes list`.
MD
cat > product/notes/notes/store.py <<'PY'
"""Notes live in one JSON file, ~/.notes.json: a list of {"id", "text", "created"} objects."""
import json
from datetime import datetime, timezone
from pathlib import Path

PATH = Path.home() / ".notes.json"


def load() -> list[dict]:
    return json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else []


def add(text: str) -> dict:
    notes = load()
    note = {"id": len(notes) + 1, "text": text, "created": datetime.now(timezone.utc).isoformat()}
    PATH.write_text(json.dumps(notes + [note], indent=2), encoding="utf-8")
    return note
PY
cat > product/notes/notes/__main__.py <<'PY'
import sys

from notes import store

if __name__ == "__main__":
    command, *rest = sys.argv[1:] or ["list"]
    if command == "add":
        print(store.add(" ".join(rest))["id"])
    else:
        for note in store.load():
            print(f'{note["id"]:>4}  {note["text"]}')
PY
commit_fixture notes
