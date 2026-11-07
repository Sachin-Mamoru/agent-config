---
description: Load and confirm the layered context (base rules, workspace, repo, team tooling) before a task
---

Follow the `ready` skill in `skills/ready/SKILL.md` of agent-config exactly (load the layers
in precedence order, report what is loaded and what is missing), then continue with whatever
task follows in this message.

This prompt file only exists for setups that still point at `commands/`. Workspaces installed
with `scripts/install.sh` get `/ready` directly from `.claude/skills/ready/`.
