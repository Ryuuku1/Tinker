#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo webapp
mkdir -p product/webapp/templates
cat > product/webapp/AGENTS.md <<'MD'
# Webapp

A one-page site served by the standard library's http.server.

## Agent playbook

- Base branch: main
- Gates: template change: `python -m unittest discover -s tests`; Python change: the same.
- Deliverable and commits: one commit per change; never push.
- Worktrees: none needed.
- Live pass: none recorded yet.
- Graph: on-demand
- Pitfalls: templates are plain HTML, no template engine.
MD
cat > product/webapp/app.py <<'PY'
"""Serves templates/index.html on http://127.0.0.1:8000/."""
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / "templates"), **kwargs)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
PY
cat > product/webapp/templates/index.html <<'HTML'
<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>Home</title></head>
  <body>
    <h1>Welcome</h1>
    <p>Your dashboard is below.</p>
  </body>
</html>
HTML
commit_fixture webapp
