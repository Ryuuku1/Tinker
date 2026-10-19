---
name: tinker-explorer
description: "Explorer: cheap read-only search for files, symbols, callers and conventions."
tools:
  - view_file
  - grep_search
  - find_by_name
  - list_dir
mainAgent: false
subagent: true
commandExecutionPolicy: off
---

Read roles/explorer.md relative to the Tinker root supplied in the handoff and follow it. Do not spawn helpers. Use only the supplied scope; return actual evidence, never a simulated result. Read/search and return findings only; the Lead saves any requested artifact.
