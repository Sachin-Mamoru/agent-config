# Workspace instructions

This folder is a multi-repo workspace. Open this folder (not a sub-repo) as the editor
folder / `claude` launch directory, so the base skills in `.claude/skills/` are discovered.

## Base rules (agent-config)

@AGENT_CONFIG_AGENTS_MD

If this session was launched inside a sub-repo, the import above and `.claude/skills/` may not
be loaded (Claude Code stops skill discovery at the repo root, and asks once before importing
a file outside the launch folder). In that case read the agent-config `AGENTS.md` yourself,
read `.claude/skills/<name>/SKILL.md` in this folder when a task matches a skill, and tell
the user to reopen this workspace folder.

## Precedence — most specific wins

1. **The repo being changed**: its `CLAUDE.md` / `AGENTS.md`, the docs they point to, and
   any skills in `<repo>/.claude/skills/`. These load when you work on files in that repo;
   read them before editing it.
2. **Team-shared tooling** for these repos (shared skills/commands checked out alongside
   them), when present.
3. **This file** — workspace-wide context.
4. **Base skills and rules from agent-config** — the generic fallback.

When two layers disagree, follow the more specific one and say which rule you followed.
Base skills fill gaps; they never override a repo's documented conventions.

## Repos in this workspace

| Folder | What it is | Start with |
|---|---|---|
| `<repo>/` | <one line> | `<repo>/CLAUDE.md` |

## Local-only rules

- <e.g. no commits/pushes unless asked; which environments may be called>
