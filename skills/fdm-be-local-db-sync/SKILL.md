# fdm-be Local DB / Migration Sync — check before starting the server

## Why this exists

fdm-be uses one shared local Postgres container (`postgres-fdm`, port 5433) across every branch
checkout. fdm-be also has ~150 diverged branches, each of which can carry its own migration
chain (see [[feedback-verify-correct-branch]] for the same "many diverged branches" problem
elsewhere). If migrations were applied while a different branch was checked out (e.g. you ran
`alembic upgrade head` on `feat/one-solution-v1`), then you switch to another branch without
downgrading first, the DB's `alembic_version` table points at a revision file that doesn't exist
in the newly checked-out branch's `alembic/versions/` — the server (or any `alembic` command)
then fails with `Can't locate revision identified by '<rev>'`, or worse, silently runs against a
schema that doesn't match the checked-out code (extra/missing columns, indexes, enum values).
This has already hit twice on record (`section-fix`, `FDM-V3`) — see
[[feedback-alembic-branch-drift]] for those specific occurrences and the origin of this
procedure.

## When to run this check

**Before starting fdm-be locally** — i.e. before running
`aws-vault exec developer -- uv run uvicorn src.fdm.main:app --reload --port 1234` (or any local
alembic command) — especially after switching branches, pulling, or rebasing. Treat "start
fdm-be locally" as always preceded by this check, not just when something visibly breaks.

## Prerequisite — `uv run alembic ...` needs a fresh CodeArtifact token, separate from AWS auth

`uv run` (even under `aws-vault exec developer --`) can fail before it ever reaches alembic:

```
× Failed to build `fdm-be @ file:///...`
╰─▶ Because hatchling was not found in the package registry ...
    hint: An index URL (https://okra-...d.codeartifact.eu-west-1.amazonaws.com/...)
    could not be queried due to a lack of valid authentication credentials (401 Unauthorized).
```

This is **not** an `aws-vault`/MFA problem — `aws sts get-caller-identity` can succeed fine while
this still fails, because `uv`'s private package index needs its own short-lived CodeArtifact
token (`UV_INDEX_OKRA_PASSWORD`), separate from the AWS session. Refresh it (per the repo's own
README "Setup AWS Credentials" section) before retrying:

```bash
export AWS_CODEARTIFACT_TOKEN=$(aws-vault exec developer -- aws codeartifact get-authorization-token \
    --domain okra --domain-owner 998607346652 --query authorizationToken --output text)
export UV_INDEX_OKRA_USERNAME=aws
export UV_INDEX_OKRA_PASSWORD="$AWS_CODEARTIFACT_TOKEN"
```

Then run the `uv run alembic ...` commands below with those exported (e.g. `aws-vault exec
developer -- env UV_INDEX_OKRA_USERNAME="$UV_INDEX_OKRA_USERNAME"
UV_INDEX_OKRA_PASSWORD="$UV_INDEX_OKRA_PASSWORD" uv run alembic heads`). The README suggests
wrapping this in a shell function (`uv-credentials-refresh`) sourced from `.zshrc`/`.bashrc` so
it doesn't need repeating per session — check whether that's already set up before assuming a
plain `uv run` will work.

## Step 1 — compare code head(s) against the DB's stamped revision

```bash
cd fdm-be
uv run alembic heads     # what the checked-out branch's migration files resolve to
uv run alembic current   # what the DB is actually stamped at
```

- If `current` matches one of `heads` exactly → in sync, nothing to do, proceed to start the
  server normally.
- If `alembic current` errors with `Can't locate revision identified by '<rev>'`, or shows a
  revision that isn't in the `heads` output → the DB is stamped from a different branch's
  migration chain. Go to Step 2.
- If `alembic current` shows an older *ancestor* of the current branch's head (a normal case,
  not drift — you just haven't migrated forward yet) → simply `uv run alembic upgrade head`, no
  need for the temp-file dance below.

## Step 2 — find where the foreign revision came from

```bash
git log --all --oneline -S"<revision_id>" -- alembic/versions
git branch -a --contains <that_commit>
```

This tells you which branch's `alembic/versions/` the DB was last migrated against.

## Step 3 — walk back to find the shared ancestor

The foreign revision's chain may be more than one migration deep (a fork with several branch-only
files, possibly through a merge revision with two `down_revision` parents). Walk the
`down_revision` chain on the **foreign branch** — via `git show <branch>:alembic/versions/<file>`
for each file — until you reach a revision id that **is** present in the current branch's own
`alembic/versions/` (check with
`grep -rhoP '^revision:\s*str\s*=\s*"\K[a-f0-9]+' alembic/versions/*.py`). That revision is the
shared ancestor to downgrade to. Collect every foreign-only file along the way — there's often
more than one (e.g. two sibling migrations that both fork from the same ancestor and later merge
back together).

**Read every foreign migration's `downgrade()` body before running anything.** Most are clean
auto-generated `add_column`/`drop_column` or index create/drop pairs — safe to round-trip. A
hand-written data backfill or type-relabeling migration (e.g. one that reclassifies rows via
`UPDATE ... SET type = 'x' WHERE ...`) can still have a well-formed, reversible downgrade, but
verify it actually undoes what it did rather than assuming any `downgrade()` is safe by
construction.

## Step 4 — materialize, downgrade, clean up, upgrade

```bash
# Temporarily restore just the foreign-only files (untracked — never `git checkout <branch> -- .`,
# per [[feedback-git-readonly-inspection]]: that would also blow away your real working tree)
git show <branch>:alembic/versions/<file>.py > alembic/versions/<file>.py
# ...repeat for every foreign-only file found in Step 3...

git status --short alembic/versions/   # confirm they show as untracked (??), not modified

uv run alembic downgrade <shared_ancestor_revision>

# Remove the temp files now that the DB no longer references them
rm alembic/versions/<file1>.py alembic/versions/<file2>.py ...
git status --short   # must be clean again before continuing

uv run alembic upgrade head
```

## Step 5 — verify

```bash
uv run alembic heads
uv run alembic current
```

These two must print the exact same revision id. If you want an extra sanity check on a
schema-shape difference (e.g. a column that only exists on the other branch), query
`information_schema.columns` for that specific table/column and confirm it's gone/present as
expected for the branch you're actually on.

## What NOT to do

- Don't run `git checkout <foreign-branch> -- alembic/versions/` or `git checkout
  <foreign-branch> -- .` to grab the files — that risks clobbering uncommitted work in your
  actual working tree. Use `git show <branch>:<path> > <path>` to materialize just the one file,
  untracked, and remove it immediately after the downgrade completes.
- Don't skip reading a foreign migration's `downgrade()` before running it, even though the two
  prior occurrences of this were both safe auto-generated migrations — a hand-rolled data
  migration might not be.
- Don't assume the foreign chain is only one migration deep — walk `down_revision` all the way
  back to an id that actually exists in the current branch's files, which may cross a merge
  revision with two parents.
- Don't leave the temporarily-materialized files in place after the downgrade — they're not
  part of the checked-out branch's real history and `git status` should be clean before you
  `alembic upgrade head`.
