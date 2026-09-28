"""Set a Tinker agent's deny rules in a Claude settings.json. Usage: python deny.py <settings.json> <role>

buzz-acp approves every permission prompt, so only deny rules and Tinker's own denies hold. Tinker already
gates commit, push, branch deletion, remote changes and Buzz workspace changes; these cover what it does not.
The image is built with the Lead's rules; every agent applies its own role's rules when it starts.
"""
import json
import sys
from pathlib import Path

BASE = ["Bash(curl:*)", "Bash(wget:*)", "Bash(env)", "Bash(env:*)", "Bash(printenv)", "Bash(printenv:*)"]
WEB = ["WebFetch", "WebSearch"]
EDITS = ["Write", "Edit", "MultiEdit", "NotebookEdit"]
ROLES = {"lead": WEB, "reviewer": WEB + EDITS, "researcher": EDITS}   # only the Researcher uses the web
path, role = Path(sys.argv[1]), sys.argv[2]
rules = BASE + ROLES[role]
data = json.loads(path.read_text(encoding="utf-8"))
deny = data.setdefault("permissions", {}).setdefault("deny", [])
deny[:] = [r for r in deny if r not in BASE + WEB + EDITS] + rules
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
print(role, json.dumps(data["permissions"]), "enabledPlugins" in data)
