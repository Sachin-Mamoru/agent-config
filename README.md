# agent-config

Personal, reusable agent configuration: base behaviour rules ([AGENTS.md](AGENTS.md)) and
skills (`skills/<name>/SKILL.md`), installed into any workspace for **Claude Code** and
**VS Code Copilot** with one command.

This repo is the base layer. Repo-specific instructions always win (see
[AGENTS.md → Precedence](AGENTS.md)):

```
1. repo being changed   <repo>/CLAUDE.md, AGENTS.md, <repo>/.claude/skills/   (most specific)
2. team-shared tooling  shared skills/commands checked out next to the repos
3. workspace            <workspace>/CLAUDE.md
4. base                 agent-config AGENTS.md + skills                        (fallback)
```

## Install into a workspace

A workspace is a folder that holds several repos side by side (e.g. `~/work/acme/` with
`backend/`, `frontend/`, and this repo cloned as `agent-config/`, or anywhere else).

```bash
git clone https://github.com/Sachin-Mamoru/agent-config.git <workspace>/agent-config
<workspace>/agent-config/scripts/install.sh --profile django-backend <workspace>
```

This creates relative symlinks (never overwriting real files):

| Path | Points to | Read by |
|---|---|---|
| `<workspace>/.claude/skills/<skill>` | `agent-config/skills/<skill>` for each profile entry | Claude Code, Copilot |
| `<workspace>/AGENTS.md` (if absent) | `agent-config/AGENTS.md` | Copilot, Codex |
| `<workspace>/CLAUDE.md` (if absent) | created from [templates/workspace-CLAUDE.md](templates/workspace-CLAUDE.md), imports AGENTS.md | Claude Code (and Copilot via `chat.useClaudeMdFile`) |

Re-run the same command after `git pull` or after editing a profile. It refreshes links and
removes links to skills dropped from the profile. Options: `--all` (every skill), `--dry-run`.
Needs bash ≥ 4 and python3.

Profiles (`profiles/*.txt`) choose which skills a workspace gets, so project-specific skills
from one codebase (e.g. `fdm-be-*`) never load into another.

## How discovery works (and the one rule to follow)

**Open the workspace folder itself** in VS Code, or run `claude` there, and type `/ready`.

- Claude Code loads `.claude/skills/` from the launch directory and its parents up to the git
  repository root. Launched *inside* a sub-repo, it stops at that repo's root and won't see the
  workspace's skills. `/ready` detects this and says so.
- `CLAUDE.md` files in parent directories always load. A sub-repo's own `CLAUDE.md` and
  `.claude/skills/` load on demand when files in it are read or edited. That's how the
  repo-specific layer joins the base layer.
- `@agent-config/AGENTS.md` in the workspace `CLAUDE.md` imports the base rules (Claude Code
  reads `AGENTS.md` natively only when no `CLAUDE.md` exists). If the import resolves outside
  the launch directory, Claude Code asks once for approval.
- Only skill names and descriptions sit in context. A skill's body and references load only when it's used.
- VS Code Copilot reads `.claude/skills/` and the root `AGENTS.md` by default
  (`chat.useAgentSkills`, `chat.useAgentsMdFile`). Skills need `name` (= folder name) and
  `description` (≤ 1024 chars) or Copilot silently skips them; `scripts/validate.py` checks this.

Docs: [Claude Code skills](https://code.claude.com/docs/en/skills),
[Claude Code memory](https://code.claude.com/docs/en/memory),
[Copilot agent skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills),
[Copilot custom instructions](https://code.visualstudio.com/docs/copilot/customization/custom-instructions).

## Skills in the `django-backend` profile

| Skill | Activates when |
|---|---|
| `ready` | Only when you type `/ready [repo-or-task]` — loads and reports the context layers |
| `django-drf-api` | Adding/changing endpoints, serializers, permissions, actions; unexpected 401/403/404; API contract, filtering, pagination, versioning |
| `django-orm-performance` | Slow endpoint/query/task, N+1, EXPLAIN/indexes, large tables, migrations' locking, Python profiling and concurrency choice |
| `django-transactions-jobs` | Concurrent state changes, lost updates, duplicates, `select_for_update`/`on_commit`, background jobs, retries, idempotency |
| `django-testing` | Writing/reviewing Django tests, reproducing and fixing bugs, flaky tests, reporting what ran |
| `django-backend-review` | Reviewing a Django diff/branch/MR, or self-review before handing a change over |
| `systematic-debugging`, `invariant-verification`, `db-constraint-design`, `architecture-best-practices`, `code-comments`, `git-hands-off`, `chat-message-voice` | Generic discipline; see each skill's description |

## Validate

```bash
python3 scripts/validate.py
```

Checks frontmatter (name = folder, lowercase-hyphen, ≤ 64; description ≤ 1024), duplicate
names, reserved names, relative links, absolute or broken symlinks, profile entries, command
frontmatter and shell syntax. Problems in profiled skills are errors; in others, warnings.

## Adding a skill

1. `skills/<name>/SKILL.md` with `name` and a `description` that says *what* and *when to use*.
2. Keep `SKILL.md` procedural (inspect → implement → verify → output); put long material in
   `skills/<name>/references/*.md` and link to it.
3. Add it to the relevant `profiles/*.txt`, run `scripts/validate.py`, then re-run
   `scripts/install.sh` for each workspace.

Never commit employer-internal details, credentials or hostnames. Machine- or employer-specific
skills stay local and are listed in [.gitignore](.gitignore).
