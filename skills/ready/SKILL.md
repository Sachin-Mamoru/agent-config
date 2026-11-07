---
name: ready
description: Load and confirm the full working context before a task — base rules (agent-config AGENTS.md), workspace CLAUDE.md, the target repo's own instructions and skills, and team-shared tooling — then report what is loaded, in precedence order, and what is missing. Run manually as /ready, optionally with a repo name or task.
disable-model-invocation: true
argument-hint: "[repo-or-task]"
---

# /ready — load context in layers, report, then continue

Arguments: `$ARGUMENTS` (a repo folder name, a task, or empty).

Do the steps in order. Read files; don't summarise from memory. Keep the final report short.

## 1. Find the workspace and the target repo

- Workspace root = the launch directory if it holds `CLAUDE.md` plus `.claude/skills/`;
  otherwise walk up from the current directory until both are found.
- List the git repos directly under it (`ls -d */.git | sed 's#/.git##'`).
- Target repo = the argument if it names one of them; otherwise the repo the task or the
  currently open file points to; otherwise none (workspace-level work).

## 2. Load the layers, most specific first

1. **Target repo**: read its `CLAUDE.md` / `AGENTS.md` in full, then the sections of the
   docs they mark as required reading (architecture, conventions, contributing). List any
   `<repo>/.claude/skills/*/SKILL.md` and `<repo>/.claude/commands/*` by name and description.
   Note the repo's own test/lint/run commands.
2. **Team-shared tooling**: if a shared skills/commands checkout exists next to the repos
   (or the target repo's docs name one), list its skills; if the docs name one that isn't
   checked out, say so.
3. **Workspace**: confirm the workspace `CLAUDE.md` is loaded and note its local-only rules.
4. **Base**: confirm the agent-config rules are loaded (build-minimal ladder, root-cause fixes,
   surgical changes, verify-before-done). List the base skills visible to you by name.
   If they aren't visible (for example, the session was launched inside a sub-repo, so the
   parent `.claude/skills/` wasn't discovered), say so and read the relevant
   `.claude/skills/<name>/SKILL.md` files directly when a task needs them.
5. **Docs tooling**: say whether a library-docs MCP (for example context7) is connected; if
   not, say that official docs will be fetched instead when version-specific detail matters.

Don't read every skill body — only names and descriptions. Bodies load when a task needs them.

## 3. Report (then continue)

```
Context ready — <workspace> → <target repo or "workspace">
Precedence: repo > team tooling > workspace > base
Repo:      <files read>; checks: <test/lint commands>
Repo skills: <names or "none">
Team tooling: <names | "not checked out: <name>" | "none found">
Workspace: CLAUDE.md loaded; local rules: <one line>
Base:      AGENTS.md loaded; skills: <names>
Missing:   <anything expected but not found, or "nothing">
```

If something expected is missing, say it plainly — don't work around it silently. Then
continue with any task that came with the command.
