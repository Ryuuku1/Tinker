"""Merge the Lead's deny rules into a Claude settings.json. Usage: python deny.py <settings.json> [extra rules...]

buzz-acp approves every permission prompt, so only deny rules and Tinker's own denies hold. Tinker already
gates commit, push, branch deletion, remote changes and Buzz workspace changes; these cover what it does not.
"""
import json
import sys
from pathlib import Path

RULES = ["WebFetch", "WebSearch", "Bash(curl:*)", "Bash(wget:*)",
         "Bash(env)", "Bash(env:*)", "Bash(printenv)", "Bash(printenv:*)"]
path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
deny = data.setdefault("permissions", {}).setdefault("deny", [])
deny += [r for r in RULES + sys.argv[2:] if r not in deny]
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(data["permissions"]), "enabledPlugins" in data)
