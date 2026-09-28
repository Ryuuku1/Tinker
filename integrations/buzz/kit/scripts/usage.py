"""Token use in this agent's Claude Code session transcripts since it started, as one JSON line (Get-KitUsage).

Claude Code writes each reply's usage into ~/.claude/projects/<folder>/<session>.jsonl; a reply with several
content blocks is logged once per block with the same message id, so each id counts once.
"""
import glob
import json
import os

replies = {}
paths = glob.glob(os.path.join(os.path.expanduser("~"), ".claude", "projects", "*", "*.jsonl"))
for path in paths:
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            message = event.get("message") if isinstance(event, dict) else None
            if event.get("type") == "assistant" and isinstance(message, dict) and message.get("usage"):
                replies[(path, message.get("id"))] = message["usage"]
totals = {"sessions": len(paths), "replies": len(replies), "input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
for usage in replies.values():
    totals["input"] += usage.get("input_tokens") or 0
    totals["output"] += usage.get("output_tokens") or 0
    totals["cache_read"] += usage.get("cache_read_input_tokens") or 0
    totals["cache_write"] += usage.get("cache_creation_input_tokens") or 0
print(json.dumps(totals))
