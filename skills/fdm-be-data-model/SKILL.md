# fdm-be Data Model / ERD

The 12-table schema behind One Solution / First Draft, verified directly against
`src/fdm/db/app/models/main.py` and `src/fdm/db/app/enums.py` (SQLAlchemy Core `Table(...)`
objects, not declarative ORM classes — this is the same `metadata_obj` that
[[reference-okra-kit]]'s `QueryEngine` and [[reference-fdm-api-reference]]'s routers/repositories
operate on). Companion skills: **okra-kit** (query engine built on these tables) and
**fdm-be-api-reference** (the endpoints that read/write them).

## Verified state — ⚠️ re-checked against `feat/one-solution-v1`, supersedes the `ai-edit-bug` check

**First verified against the wrong branch** (`ai-edit-bug` @ `e185254`); Sachin flagged this and
it was re-checked against `feat/one-solution-v1` @ `61bea9c`, the actual One Solution branch.
The two branches have genuinely different schemas — this isn't "one is behind the other," it's
two parallel feature branches with non-overlapping changes. Confirmed differences:

| Field | `ai-edit-bug` (2026-09-16) | `feat/one-solution-v1` (2026-09-16) | `feat/one-solution-v1` (2026-09-21, post `develop` merge) |
|---|---|---|---|
| `projects.is_pinned` | absent | **present** (Boolean, NOT NULL, default `false`) | present |
| `projects.language` | absent | **present** (Text, NOT NULL, default `'American English'`, app-validated against `ProjectLanguage`) | present |
| `jobs.retry_of_job_id` | **present** (self-FK, SET NULL) | absent | **present again** — reintroduced when `feat/one-solution-v1` merged `develop` (commit `e742136`, 2026-09-21) |

`retry_of_job_id` flipping back within 5 days on the *same branch* (not a different one) is the
strongest evidence yet that a `develop` merge, not just switching branches, can silently change
which columns/routes exist — re-verify after any merge shows up in `git log`, not only after a
branch switch.

Everything else below — base columns, all other tables' columns, naming (`tasks.job_id`/`type`),
the `agent_cache` unique-constraint gap, `assets.asset_hash` NOT NULL, no `users` table — was
re-confirmed identical on both branches. **Given this schema has already been shown to diverge
between two branches, re-run the verification query below on whatever branch you're actually
targeting before trusting a specific "does column X exist" claim.**

Verification query used both times: `sed -n '/^<table> = Table(/,/^)/p' src/fdm/db/app/models/main.py`.

The rest of this section documents what's confirmed true on **`feat/one-solution-v1`**
(current), with the `ai-edit-bug` divergences called out inline where relevant:

- **There is no `users` table in fdm-be.** Every "owned by a user" column
  (`projects.user_id`, `feedback.user_id`, `user_assets.user_id`, and `created_by` from
  `base_columns()`) is plain `Text`, **not a UUID foreign key to any local table**. User identity
  is an external concept owned by Core (a separate service/database, IAM-authenticated — see
  `env-mapping` skill), passed in via the `X-Portal-UserId` header and stored as an opaque
  string. An ERD box labeled "USERS / CORE" represents that external system, not a real fdm-be
  table — don't go looking for a `users` migration here, and don't add a real FK constraint to
  `created_by`/`user_id` (there's nothing in this database to point it at).
- **`base_columns()` (`db/app/models/base.py`) is exactly**: `id` (UUID, PK, `uuid7()` default),
  `created_at`/`updated_at` (TIMESTAMPTZ, DB-side `timezone('utc', now())` defaults),
  `deleted_at` (TIMESTAMPTZ, nullable — soft delete), `created_by` (**Text**, not UUID, not an
  FK — see above). Every one of the 12 tables includes these five via `*base_columns()`.
- **Fields that look "new" (e.g. highlighted) in some ERD versions and their real status, on
  `feat/one-solution-v1`**:
  - `jobs.retry_of_job_id` — **not on this branch.** It exists on `ai-edit-bug` (self-referencing
    nullable FK, `jobs.id`, `ondelete="SET NULL"`, backing `POST /jobs/{job_id}/retry`) but
    `feat/one-solution-v1`'s `jobs` table has no such column and no retry route. Don't assume
    job-retry is universally available.
  - `projects.is_pinned` — **real**: `Column("is_pinned", Boolean, nullable=False,
    server_default=text("false"), index=True)`. Backs `PATCH /projects/pinned` in the
    API-reference skill.
  - `projects.language` — **real**: `Column("language", Text, nullable=False,
    server_default=text(f"'{DEFAULT_PROJECT_LANGUAGE}'"))`. Stored as plain `Text`, not a native
    Postgres enum — validated at the app layer against a Python `ProjectLanguage` StrEnum
    (`American English` [default], `British English`, `Spanish`, `French`, `German`, `Italian`,
    `Portuguese`) specifically so adding a new language is a code change, not a migration. The
    "reject language change once a draft exists" business rule from the ticket is **not**
    implemented — `ProjectService.update_project` writes whatever fields are given with no such
    guard (see API-reference skill).
  - `revisions.description` — there's no column literally named `description`; the closest real
    field is `revisions.origin_description` (Text, nullable), already used by
    `PATCH /revisions/{revision_id}`. Treat "description" in any ERD as referring to that
    existing column, not a new one to add. (Unchanged on both branches.)
- **Naming/shape mismatches worth knowing before writing a query or migration**:
  - `tasks.job_id` — some diagrams show `jobs_id`; the real column is singular: `job_id`.
  - `tasks.type` — some diagrams show `task_type`; the real column is just `type` (the Python
    enum type is `TaskType`, but the column name is not).
  - `agent_cache`'s real uniqueness is `UniqueConstraint("task_type", "input_hash")` —
    **`cache_version` is not part of the unique key**, despite some diagrams implying a
    three-column composite (`task_type`, `input_hash`, `cache_version`). A new row with a bumped
    `cache_version` for the same `(task_type, input_hash)` would violate this constraint as
    written — check with whoever owns cache-invalidation logic before assuming versioning works
    that way.
  - `assets.asset_hash` is `nullable=False` — not nullable, despite some diagrams marking it
    `(null)`. It also has a partial unique index (`uq_asset_hash`, unique where
    `deleted_at IS NULL`) used for dedup, and a `CheckConstraint` requiring **exactly one** of
    `content_json`/`s3_key` to be set (not both, not neither) — neither the constraint nor the
    dedup index is usually shown on a simple ERD box.
- **Columns real diagrams commonly omit** (all verified present in code):
  - `jobs.revision_id` — nullable UUID, but **no FK constraint** on it (unlike `project_id`/
    `project_section_id` on the same table, which are real FKs). Likely intentional (the
    revision may not exist yet when a job starts), but don't assume referential integrity is
    enforced here at the DB level.
  - `jobs.failure_acknowledged_at` (nullable timestamp) — backs
    `POST /jobs/{job_id}/acknowledge-failure`.
  - `tasks.celery_task_id` (nullable, indexed) — links a task row to the actual Celery task ID.
  - `revisions.schema_version` (Integer, default `1`) — see project memory on section-config
    work; revisions on schema_version 1 are treated as read-only by newer code paths.
  - `project_assets.source_asset_id` (nullable FK → `assets.id`) and `project_assets.udp_status`
    (nullable `Status` enum) — `udp_status` is exactly the field the upload-progress UI in the
    API reference skill polls; it's easy to miss on a simplified ERD box.
  - `assets.version_id` (nullable Text).
  - `user_assets.section_id` (nullable FK → `sections.id`) — scopes a user-saved config template
    to a section type; this table is what backs the `/configs` endpoints in the API reference
    skill (`user_asset_type` is the real column name, not "asset_type").

## Base model (real, `db/app/models/base.py`)

Inherited by all 12 tables via `*base_columns()` — not a physical table itself:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK, default `uuid7()` |
| `created_at` | TIMESTAMPTZ | DB-side default `timezone('utc', now())` |
| `updated_at` | TIMESTAMPTZ | same default, `onupdate` refreshes it |
| `deleted_at` | TIMESTAMPTZ, nullable | soft-delete marker — `okra_kit`'s `ScopePolicy` auto-filters `WHERE deleted_at IS NULL` whenever this column is present |
| `created_by` | **Text**, not null | opaque external user id string — no FK, no `users` table exists |

## Tables (verified columns beyond base_columns)

**`sections`** — reusable section definitions (not project-scoped):
`section_type` (enum, indexed), `name` (nullable), `description` (nullable).

**`project_sections`** — join of a project to its sections, per-project state:
`section_id` (FK→sections, CASCADE), `project_id` (FK→projects, CASCADE), `section_type` (enum,
denormalized from `sections` for query convenience), `status` (enum), `current_revision_id`
(nullable FK→revisions, SET NULL), `meta_data` (JSONB, nullable). Unique on `(project_id,
section_id)`.

**`projects`** (on `feat/one-solution-v1`): `user_id` (Text), `name`, `description` (nullable),
`status` (`ProjectStatus` enum), `is_pinned` (Boolean, NOT NULL, default `false`), `language`
(Text, NOT NULL, default `'American English'`, app-validated against `ProjectLanguage`). Neither
`is_pinned` nor `language` exist on `ai-edit-bug` — see Verified state.

**`jobs`**: `project_id` (FK→projects, CASCADE), `project_section_id` (nullable FK→
project_sections, SET NULL), `workflow_type` (enum), `priority` (enum), `status` (enum),
`revision_id` (nullable UUID, **no FK**), `meta_data` (JSONB, nullable),
`failure_acknowledged_at` (nullable timestamp), `retry_of_job_id` (nullable self-FK, SET NULL —
present as of 2026-09-21; was absent on `feat/one-solution-v1` for a few days after this branch
diverged from `ai-edit-bug`, then came back via a `develop` merge — see Verified state table).

**`tasks`**: `job_id` (FK→jobs, CASCADE — column is `job_id`, not `jobs_id`), `type` (`TaskType`
enum — column is `type`, not `task_type`), `priority` (enum), `description` (nullable),
`status` (enum), `celery_task_id` (nullable, indexed), `meta_data` (JSONB, nullable).

**`revisions`**: `project_id` (FK→projects, CASCADE), `project_section_id` (nullable FK→
project_sections, SET NULL), `job_id` (nullable FK→jobs, SET NULL), `parent_revision_id`
(nullable self-FK, SET NULL), `major_version`/`minor_version` (Integer), `status` (enum),
`origin` (`ContentOrigin` enum), `origin_description` (nullable Text), `schema_version`
(Integer, default `1`). Partial unique index on `(project_id, project_section_id, major_version,
minor_version)` **only where `status = 'completed'`** — soft-deleted/non-completed revisions
don't block a version number from being reused.

**`assets`** — the global content-addressed store: `asset_type` (enum), `format_version`
(Integer, default 1), `file_name` (nullable), `content_json` (JSONB, nullable), `s3_key`
(nullable), `asset_hash` (Text, **not** nullable — dedup key), `meta_data` (JSONB, nullable),
`version_id` (nullable Text). `CheckConstraint`: exactly one of `content_json`/`s3_key` must be
set. Partial unique index on `asset_hash` where `deleted_at IS NULL`.

**`project_assets`** — link table, project/section ↔ asset: `project_id` (FK→projects,
CASCADE), `project_section_id` (nullable FK→project_sections, SET NULL), `asset_id` (FK→assets,
CASCADE), `source_asset_id` (nullable FK→assets, SET NULL — the upload that produced this
`udp_extract` row), `project_asset_type` (enum), `file_name` (nullable), `udp_status` (nullable
`Status` enum — the upload-progress field). Several partial unique indexes enforce different
uniqueness rules per `project_asset_type` (see source for the exact `postgresql_where` clauses
if writing a migration against this table).

**`revision_assets`**: `revision_id` (FK→revisions, CASCADE), `asset_id` (FK→assets, CASCADE),
`revision_asset_type` (enum). Unique triplet `(revision_id, asset_id, revision_asset_type)`.

**`agent_cache`**: `project_id` (FK→projects, CASCADE), `project_section_id` (nullable FK→
project_sections, SET NULL), `asset_id` (FK→assets, CASCADE), `task_type` (enum, indexed),
`input_hash` (Text, indexed), `cache_version` (Integer, default 1). Unique on `(task_type,
input_hash)` only — see Verified state re: `cache_version` not participating in uniqueness.

**`feedback`**: `revision_id` (FK→revisions, CASCADE), `user_id` (Text), `category`
(`FeedbackCategory` enum), `sentiment` (`SentimentType` enum), `comment` (nullable).

**`user_assets`** — backs the `/configs` config-template API: `user_id` (Text), `asset_id`
(FK→assets, CASCADE), `user_asset_type` (enum — currently only `CONFIG` is defined), `name`,
`section_id` (nullable FK→sections, SET NULL — scopes a template to a section type). Unique on
`(user_id, name, section_id, user_asset_type)`, plus a partial unique index covering the
`section_id IS NULL` case (Postgres `UNIQUE` doesn't treat `NULL`s as equal, so a plain
constraint alone wouldn't catch duplicate global templates).

## Enums (verified, `db/app/enums.py` — complete value lists)

| Enum | Values |
|---|---|
| `WorkflowType` | `udp`, `generation`, `regeneration`, `refinement`, `export`, `evaluation`, `config_generation` |
| `TaskType` | `udp`, `extractor`, `author`, `evaluator`, `exporter`, `refiner`, `agent_prompt`, `table_reader`, `outline_generator`, `table_generator`, `results_author` |
| `ContentOrigin` | `generated`, `manual_edit`, `ai_assisted_edit`, `regenerated` |
| `SentimentType` | `like`, `neutral`, `dislike` |
| `UploadAssetType` | `protocol`, `additional_material` (client-upload allowlist — narrower than `AssetType`) |
| `AssetType` | `config`, `extraction`, `udp_extract`, `draft`, `evaluation`, `citation`, `protocol`, `additional_material`, `agent_prompt`, `export`, `table_index`, `aggregated_table_index`, `table_artifacts` |
| `RevisionAssetType` | `config`, `extraction`, `draft`, `evaluation`, `citation`, `export` |
| `ProjectAssetType` | `protocol`, `additional_material`, `udp_extract`, `table_index`, `config`, `aggregated_table_index`, `table_artifacts` |
| `Priority` | `high`, `medium`, `low` |
| `Status` | `pending`, `in_progress`, `completed`, `failed`, `cancelled` |
| `ProjectStatus` | `active`, `archived`, `deleted` |
| `FeedbackCategory` | `draft_quality`, `citation_quality`, `extraction_quality`, `other` |
| `AssetContentSource` | `s3`, `db` |
| `SectionType` | `materials_and_methods`, `introduction`, `results` |
| `UserAssetType` | `config` (only value defined today) |
| `ProjectLanguage` (on `feat/one-solution-v1` only) | `American English` (default), `British English`, `Spanish`, `French`, `German`, `Italian`, `Portuguese` — stored as plain `Text` on `projects.language`, not a native Postgres enum, specifically so a new language is a code change, not a migration |

All enums are Python `StrEnum` stored as **non-native Postgres enums** (`native_enum=False`,
via the local `_pg_str_enum()` helper) — this is deliberate: native `str(StrEnum.MEMBER)` on
Python 3.11+ returns `"ClassName.MEMBER"` instead of the value, which breaks SQLAlchemy's
default enum deserialization. Don't "fix" this to a native Postgres enum without understanding
why — that comment in the source is the reason.

## Key relationships worth knowing (not just column-level FKs)

- `projects (1) → project_sections (1..*) → revisions (0..*)`, with `project_sections.
  current_revision_id` pointing back to whichever revision is "live" for that section.
- `revisions.parent_revision_id` is a self-FK — revisions form a version chain per section, not
  just a flat list (see the partial-unique-index note above for how version numbers are scoped).
- `jobs.retry_of_job_id` is a self-FK — a retry job points back at the job it retried, forming
  its own chain distinct from the revision chain.
- `agent_cache` and `revision_assets`/`project_assets` all point at the same central `assets`
  table — `assets` has no knowledge of which project/revision/task uses it; that link always
  lives on the join table's side (this is the "centralized asset store" design called out in the
  entity descriptions).

## What NOT to do

- Don't add a real FK constraint from `created_by`/`user_id`/etc. to a `users` table — no such
  table exists in this database; user identity is external (Core).
- Don't assume `projects.is_pinned`, `projects.language`, or `jobs.retry_of_job_id` exist (or
  don't) without checking the live migrations on whatever branch you're actually working on —
  all three have already been proven to differ between `ai-edit-bug` and `feat/one-solution-v1`,
  and `retry_of_job_id` additionally flipped twice on `feat/one-solution-v1` alone within 5 days
  (a `develop` merge, not a branch switch, was the cause the second time).
- Don't assume `agent_cache`'s uniqueness includes `cache_version` — it's `(task_type,
  input_hash)` only, as written today (confirmed unchanged on both branches).
- Don't rename `tasks.job_id`→`jobs_id` or `tasks.type`→`task_type` to "match" an ERD — the ERD
  is wrong here, the code is right (confirmed unchanged on both branches).
- Don't treat `jobs.revision_id` as FK-enforced — it isn't, unlike the other job FKs.
