---
name: db-constraint-design
description: >
  How to design or review a UNIQUE constraint/index in Postgres (fdm-be, udp-celery) so it
  actually enforces what it's meant to — especially partial indexes using postgresql_where.
  Use whenever writing or reviewing an Alembic migration that adds/changes a unique constraint,
  or an application-level duplicate/conflict pre-check that's supposed to mirror one.
---

# Postgres Unique Constraint Design — fdm-be / udp-celery

## The mistake this exists to prevent

From fdm-be's One Solution migration (`5cd65fd48a35_drop_project_section_id_from_project_.py`),
the index was first written as:

```python
op.create_index(
    "uq_project_assets_file_name", "project_assets",
    ["project_id", "file_name"],  # file_type missing here
    unique=True,
    postgresql_where=sa.text("file_type IS NOT NULL"),
)
```

`file_type` appeared in `postgresql_where` but not in the column list. That clause only decides
**which rows the constraint looks at** (here: "only rows with a file_type set, i.e. user
uploads, not system-generated rows") — it does nothing to make `file_type` part of what must be
unique. The real key was just `(project_id, file_name)`, so a `protocol` and a `reference` that
happened to share a file name would have collided. Fixed by moving `file_type` into the key:
`["project_id", "file_type", "file_name"]`. Caught in review, not by a test — the test suite had
no case exercising two different-typed files with the same name.

## The one question that catches it

Before finalizing any unique index/constraint, state in one sentence: **"Two rows are
duplicates of each other when ___."** Every column named in that sentence must be in the
constraint's key columns. If a column shows up in `postgresql_where` (or a `CheckConstraint`)
but not in the key, ask explicitly why — usually it belongs in both, or it doesn't belong in the
WHERE clause at all.

`postgresql_where` and the key columns answer two different questions:
- **Key columns**: what combination must be unique?
- **`postgresql_where`**: which rows does this constraint even look at?

A scoping concept needs to be in *both* when it changes what "duplicate" means (a `protocol`
and a `reference` are never duplicates of each other, no matter the name — so `file_type` is
part of identity). It only belongs in the WHERE clause when it's purely about which rows are
exempt from the check at all (`deleted_at IS NULL` never needs to be a key column — a
soft-deleted row isn't "a different kind of duplicate," it's just not a candidate).

Don't assume every `postgresql_where`-only column is automatically suspect, either — two unique
indexes can legitimately coexist on the same table with different scopes for different reasons.
`project_assets` also carries `uq_project_assets_material_per_section` (type **is** in its key —
it's an asset-linkage-identity constraint: "was this exact asset linked to this section as this
type before?") alongside a separate, deliberately type-agnostic filename-collision guard scoped
only by section ("don't let two files share a display name in this section's list, regardless
of sub-type"). Two constraints, two different duplicate-definitions, both correct. The test
above is what tells them apart — don't pattern-match on "column only in WHERE" as an automatic
red flag without asking what that specific constraint's job actually is.

## Mirror the constraint in application-level checks

If a repository/service pre-checks for a conflict before insert (e.g.
`check_file_name_exists_for_project`), its query must filter on *exactly* the same columns as
the DB constraint's key — not a subset. A looser pre-check (e.g. `file_type IS NOT NULL` instead
of `file_type == <the specific type>`) rejects uploads the DB would actually allow, and the two
can silently drift apart if only one side is ever updated later. Treat the DB key columns as the
source of truth and derive the app check's filter from them, not the reverse.

## Verification step before shipping

Write two concrete example rows that must be allowed to coexist, and two that must collide,
using the real entity — not `foo`/`bar`. If any column named in the "why these are different"
reasoning isn't in the key list, the index is wrong.

For `uq_project_assets_file_name`:
- **Must coexist**: `(project A, protocol, "summary.pdf")` and `(project A, reference,
  "summary.pdf")` — different `file_type`, same name, same project → proves `file_type` must be
  a key column, not just a filter.
- **Must collide**: `(project A, protocol, "summary.pdf")` uploaded twice → same everything →
  must collide.

## What NOT to do

- Don't put a column in `postgresql_where` because it "feels related" to the row without first
  checking whether it changes what counts as a duplicate — if it does, it belongs in the key
  list too.
- Don't treat every WHERE-only column as automatically wrong, either — check what that specific
  constraint's job is (see the two-constraints-on-one-table example above) before "fixing" it.
- Don't trust an app-level duplicate pre-check just because it passes tests that don't cover
  cross-scope collisions — write the must-coexist case from the Verification step as an actual
  test, not just the happy path.
- Don't skip this for constraints that "look simple" — this exact mistake happened on a
  two-column-turned-three-column index, not something exotic.

## See also

`invariant-verification` — the general form of this technique, for any rule-encoding code, not
just Postgres constraints (authorization checks, state-transition guards, dedup logic
elsewhere). This skill is the specific worked example it was generalized from.
