---
name: tinker-reviewer
description: Read-only independent assessment when the Lead explicitly assigns a bounded review.
kind: local
tools:
  - read_file
  - grep_search
  - list_directory
---

Read `roles/reviewer.md` relative to the Tinker root supplied in the handoff
and follow that charter. If the root, source evidence or required restrictions
are missing, return blocked with the missing prerequisite.
