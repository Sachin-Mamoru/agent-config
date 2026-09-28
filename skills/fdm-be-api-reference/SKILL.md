# FDM Backend API Reference (fdm-be)

Resource-by-resource reference for the endpoints a frontend (or another service) calls against
fdm-be. For the generic query-param system (filtering, expand, pagination, sorting) used across
most GET/list endpoints, see the **okra-kit** skill — this doc only covers what each endpoint
actually accepts/returns on top of that.

## Verified state — ⚠️ re-checked 2026-09-15 against `feat/one-solution-v1`, supersedes the `ai-edit-bug` check

**This was first verified against the wrong branch.** The initial pass below was done against
`ai-edit-bug` @ `e185254`. Sachin flagged that this was the wrong branch for One Solution work;
re-checking against `feat/one-solution-v1` @ `61bea9c` (the actual One Solution branch — last
merge is `feat/EAE-993/config-for-language`) turned up real differences, not just noise. **fdm-be
has many long-lived parallel feature branches with genuinely different schemas/endpoints** — a
finding from one branch does not transfer to another. Re-run the greps in each section before
trusting anything here on a third branch.

Differences found between the two branches:
- **`PATCH /projects/pinned` (pin/unpin) is real on `feat/one-solution-v1`** — `ai-edit-bug` was
  simply missing it (behind, as originally suspected). Moved from "Unverified" into the Projects
  table below.
- **`POST /jobs/{job_id}/retry` status changed twice in one week — re-verify before trusting
  either direction.** As of 2026-09-16, it did not exist on `feat/one-solution-v1` (present only
  on `ai-edit-bug`, via `jobs.retry_of_job_id`). As of 2026-09-21, after `feat/one-solution-v1`
  merged `develop` in (commit `e742136`), **it's back** — `retry_of_job_id` and the route both
  exist again, and `JobsService.retry_job` (`services/jobs.py:737`) reuses each workflow's own
  resume/retry path (`DraftGenerationService.resume_draft_generation`,
  `RefinementService.retry_refinement_job`, etc.) rather than being generic. This is the clearest
  proof yet that "exists on branch X" has a shelf life measured in days here, not just "differs
  between branches" — a `develop` merge can silently reintroduce or remove a feature on a branch
  you already checked. Always re-grep after `git log` shows a merge from another branch, not just
  after switching branches yourself.
- **The project `language` field is real** on `feat/one-solution-v1` — `PATCH
  /projects/{project_id}` accepts `language: ProjectLanguage` and it's persisted. What's still
  true from the original check: there is **no guard rejecting a language change once a draft
  exists** — `ProjectService.update_project` applies whatever fields are given with no such
  check. So: the field exists, the specific business rule from the ticket doesn't.
- `POST /projects/{project_id}/assets/files/retry` and `DELETE
  .../assets/{asset_id}/tables/{table_id}` — still not found on `feat/one-solution-v1` either.
  Still unverified/unbuilt as far as any branch checked so far shows.
- The jobs/tasks path-doubling bug (below) and everything else in this doc — re-confirmed
  identical on both branches.

Original checks, still accurate on `feat/one-solution-v1` unless noted above — verified directly
against `src/fdm/routers/*.py`, `src/fdm/routers/api.py` (the `include_router` mounts),
`src/fdm/main.py`, `src/fdm/schemas/common.py`, and `tests/perf/stress_test.py`:

- **Base path / auth / envelope are accurate**: `ROUTER_PREFIX = "/api/v1"` (`main.py`);
  `X-Portal-UserId` header; `WrappedResponse`/`WrappedListResponse` (`schemas/common.py`) really
  do produce `{"status": "success", "code": 200, "metadata": {...}, "data": ...}`.

- **Two real path-doubling bugs**, found by reading the router mount prefixes in
  `src/fdm/routers/api.py` against the route decorators inside each router file — the commonly
  circulated doc describes the *intended* REST shape, not what's actually mounted:
  - **Jobs**: `jobs_router` is mounted with `prefix="/jobs"`, but its own routes are declared as
    `@router.post("/projects/{project_id}/jobs")` / `@router.get("/projects/{project_id}/jobs")`.
    The real live path is **`/api/v1/jobs/projects/{project_id}/jobs`**, not
    `/api/v1/projects/{project_id}/jobs`. Confirmed independently — `tests/perf/stress_test.py`
    and `tests/perf/fixtures/collect_draft_seeds.py` both call the doubled path.
  - **Tasks**: `tasks_router` is mounted with `prefix="/tasks"`, route declared as
    `@router.get("/jobs/{job_id}/tasks")`. Real live path is
    **`/api/v1/tasks/jobs/{job_id}/tasks`**, not `/api/v1/jobs/{job_id}/tasks`.
  - Every other resource (projects, sections, project-assets, revisions, feedback, configs,
    agent-cache) mounts cleanly with no doubling — this is specific to jobs/tasks.

- **Real endpoints that exist but are easy to miss** (not always covered by summaries of this
  API):
  - `POST /api/v1/projects/{project_id}/assets` (`link_asset_to_project`) — a direct link
    endpoint, separate from the presign/confirm-upload S3 flow below.
  - Generic revision-asset CRUD on `revisions.py`, lower-level than the typed getters:
    `POST /revisions`, `GET /revisions/{revision_id}/assets`,
    `POST /revisions/{revision_id}/assets`, `GET/PATCH/DELETE /revisions/{revision_id}/assets/{asset_id}`.
  - `PATCH /api/v1/projects/pinned` (`set_projects_pinned`) — bulk pin/unpin, confirmed real on
    `feat/one-solution-v1` (see full description in the Projects section below).
  - `hidden_section_types` (`settings.py:112`) — a feature-gate setting for hiding section types
    from API responses per environment. **Declared but not wired up anywhere** — zero consumers
    in any router or service as of 2026-09-21. Don't assume Results (or any section) is actually
    gated by this in any environment; the setting exists, the enforcement doesn't yet.

- **`POST /jobs/{job_id}/retry` and `jobs.retry_of_job_id` exist on `ai-edit-bug` but NOT on
  `feat/one-solution-v1`** — don't assume job-retry is universally available; it's branch-specific
  as of this check.

- **"Retry all failed files" (`/assets/files/retry`) and "delete single extracted table"
  (`DELETE .../tables/{table_id}`) still don't exist on any branch checked so far** (`ai-edit-bug`
  or `feat/one-solution-v1`). Treat as unverified/unbuilt until checked against whatever branch
  you're actually working on.

- **The project `language` field is real; the draft-guard business rule is not.**
  `PATCH /projects/{project_id}` accepts `language: ProjectLanguage` (7 values: American English,
  British English, Spanish, French, German, Italian, Portuguese) via `ProjectMetadata`, and
  `ProjectService.update_project` persists it unconditionally — there is no check anywhere for
  "reject if a draft already exists for this project." If asked to implement that rule, it's new
  logic to add to `update_project`, not a bug in existing logic.

**How to re-verify if this drifts**: `grep -n "@router\.\(get\|post\|patch\|delete\)(" src/fdm/routers/*.py`
plus reading each file's `APIRouter()`/`prefix=` mount in `src/fdm/routers/api.py` gives the
ground truth for real paths — do this again before trusting the tables below if the routers have
changed since 2026-09-15.

## Response envelope

Single-item response:
```json
{ "status": "success", "code": 200, "metadata": { "version": "1.2.3" }, "data": { } }
```

List/paginated response — `data` is an okra_kit `Page`:
```json
{
  "data": {
    "results": [ ],
    "meta": { "total_items": 42, "current_page": 1, "current_page_size": 10, "total_pages": 5, "next": "…", "previous": null }
  }
}
```

## Query params (pagination/filter/expand/sort)

Most GET/list endpoints accept the full okra_kit param set (`page`, `page_size`, `order_by`,
`expand` incl. inline filters, `include_fields`/`exclude_fields`, `<field>__<op>=value`,
`<relation>__<field>=value`). See the **okra-kit** skill for the complete operator/limit
reference — that skill also flags that free-text `search=` is documented in places but not
actually implemented in `okra_kit` itself, so don't rely on it here either.

## 1. Projects

| Method & Path | Purpose |
|---|---|
| `POST /projects` | Create a project. Auto-creates Introduction and Materials & Methods sections. |
| `GET /projects` | List the user's projects, paginated. |
| `GET /projects/{project_id}` | Get one project. |
| `PATCH /projects/{project_id}` | Update name/description (see language-update caveat above — no `language` field exists yet). |
| `DELETE /projects/{project_id}` | Soft-delete a project. |
| `POST /projects/{project_id}/assets` | Link an asset to the project directly (`link_asset_to_project`) — distinct from the presign/confirm-upload flow. |
| `PATCH /projects/pinned` | Bulk pin/unpin: `{ "project_ids": [...], "is_pinned": true }`, 1-100 UUIDs, batched under one call (`set_projects_pinned`). Real on `feat/one-solution-v1`; re-check on other branches. |

Recommended pattern for a project view — one request instead of three, using okra_kit inline
expand filters:
```
GET /projects/{id}?expand=project_sections(section_type=results),project_assets(project_section__section_type__include=null|results)&include_fields=id,project_sections,project_assets
```

Project object (on `feat/one-solution-v1`):
```json
{ "id": "uuid", "name": "My Study", "description": "…", "status": "active", "is_pinned": false,
  "language": "American English", "created_at": "…", "updated_at": "…" }
```
`is_pinned`/`language` are real columns on `feat/one-solution-v1` but not necessarily every
branch — see Verified state.

## 2. Project Sections

Every project has up to three sections: `introduction`, `materials_and_methods`, `results`.

| Method & Path | Purpose |
|---|---|
| `GET /projects/{project_id}/sections` | List all sections for the project. |
| `GET /projects/{project_id}/sections/{section_type}` | Get one section. |
| `PATCH /projects/{project_id}/sections/{section_type}` | Set the current revision: `{ "current_revision_id": "uuid" }`. |

```json
{ "id": "uuid", "project_id": "uuid", "section_type": "results", "status": "completed", "current_revision_id": "uuid|null", "meta_data": {} }
```

## 3. Project Assets

Link table between a project and its files/generated outputs. `project_asset_type`: `protocol`
\| `additional_material` \| `udp_extract` \| `table_index` \| `aggregated_table_index` \|
`table_artifacts` \| `config`.

**Uploading a file — 2-step, direct-to-S3:**
```
POST /projects/{project_id}/assets/presign
```
```json
// request
{ "file_name": "protocol.pdf", "file_size_bytes": 204800, "content_type": "application/pdf",
  "project_asset_type": "protocol", "checksum_sha256": "base64-sha256" }
// response
{ "upload_id": "signed-token", "url": "https://s3...", "fields": { "...": "..." }, "expires_at": "…" }
```
`project_section_id` is required when `project_asset_type` is `additional_material`. Browser
POSTs the file directly to the returned S3 `url`/`fields`, then:
```
POST /projects/{project_id}/assets/confirm-upload
{ "upload_id": "signed-token" }
```
Creates the Asset + ProjectAsset, starts UDP extraction, returns `{ "asset_id": "uuid", "job_id": "uuid" }`
— poll `job_id` per the Jobs section (note the corrected path below).

**Listing assets:**
```
GET /projects/{project_id}/assets?project_asset_type__include=protocol|additional_material&project_section__section_type__include=null|results&expand=asset&include_fields=asset.content
```
- `expand=asset` nests the underlying asset (`asset_type`, `s3_key`, `content_json`).
- Including `asset.content` pulls the S3 file body into the response — costs an S3 round-trip
  per row, use sparingly.

```json
{
  "id": "project-asset-uuid", "project_id": "uuid", "project_section_id": "uuid|null",
  "asset_id": "uuid", "source_asset_id": "uuid|null",
  "project_asset_type": "udp_extract", "file_name": "protocol.pdf",
  "udp_status": "pending|in_progress|completed|failed|cancelled|null"
}
```
Poll this (or the single asset) for an upload-progress UI, keyed on `udp_status`.

| Method & Path | Purpose |
|---|---|
| `DELETE /projects/{project_id}/assets/{asset_id}?project_section_id=` | Unlink a protocol/additional material. 409 if a job depends on it. |
| `PATCH /projects/{project_id}/assets/{asset_id}` | System-only (UDP worker reports `udp_status`) — not for frontend use. |

**Reading extracted tables (Results section)** — once UDP extraction finishes, a Table Index
asset appears:
```
GET /projects/{project_id}/assets?project_asset_type=table_index&expand=asset
```
`asset.content_json.tables`:
```json
{ "tables": [ { "table_id": "t1", "label": "Baseline Demographics", "page_start": 4, "page_end": 6,
    "page_count": 3, "s3_key": "fdm/outputs/protocol.pdf", "table_pdf_s3_key": "fdm/outputs/t1.pdf" } ] }
```
Pass chosen `table_id`/`label`/`s3_key` into a job's `meta_data.selected_data_sources` (see Jobs).

## 4. Assets (direct)

Lower-level creation path, used when an asset needs to exist outside the project-upload context.

| Method & Path | Purpose |
|---|---|
| `POST /assets` (multipart) | Create an asset directly. `file` required for draft/protocol/udp_extract/additional_material; `content_json` required for config/extraction/evaluation/citation. |
| `POST /assets/from-s3` | System-only — registers a file a backend process already wrote to S3. |

## 5. Jobs — ⚠️ path differs from what you might expect

A job is a unit of async backend work (generation, refinement, export, UDP, config generation).

| Method & Real Path | Purpose |
|---|---|
| `POST /jobs/projects/{project_id}/jobs` | Create/kick off a job. **Not** `/projects/{project_id}/jobs` — see Verified state. |
| `GET /jobs/projects/{project_id}/jobs` | List jobs for a project. Same doubling. |
| `GET /jobs/{job_id}` | Job detail with task progress — poll this while a job runs. |
| `POST /jobs/{job_id}/cancel` | Cancel a running job. |
| `POST /jobs/{job_id}/acknowledge-failure` | Dismiss a failed job's error state. |

`POST /jobs/{job_id}/retry` — status has flipped twice in a week on `feat/one-solution-v1` alone
(absent 2026-09-16, present again 2026-09-21 after a `develop` merge). Re-grep
`jobs.retry_of_job_id` in `main.py` and `retry` in `routers/jobs.py` on whatever checkout you
actually have before assuming either way.

Filter server-side rather than pulling everything client-side:
```
GET /jobs/projects/{project_id}/jobs?workflow_type__include=generation|refinement&status__include=in_progress|failed&project_section__section_type__include=results&order_by=-created_at&expand=tasks
```

Create body:
```json
{ "workflow_type": "generation", "project_section_id": "uuid", "priority": "medium", "meta_data": {} }
```
`workflow_type`: `udp`, `generation`, `regeneration`, `refinement`, `export`, `evaluation`,
`config_generation`. `generation`/`regeneration`/`udp`/`config_generation` require
`project_section_id`; `refinement`/`export`/`evaluation` require `revision_id` instead.

`meta_data.selected_data_sources` tells generation which files/tables to use:
```json
"meta_data": {
  "selected_data_sources": [
    { "source_asset_id": "protocol-asset-uuid", "udp_extract_asset_id": "udp-extract-asset-uuid",
      "metadata": { "tables": [ { "id": "t1", "name": "Baseline Demographics", "s3_key": "fdm/outputs/t1.pdf" } ] } }
  ]
}
```
`metadata.tables` only applies to the Results section (table-level selection); for
Introduction/Materials & Methods, omit `metadata` and reference the whole source/extract.

```json
{
  "id": "uuid", "project_id": "uuid", "project_section_id": "uuid", "section_type": "results",
  "workflow_type": "generation", "priority": "medium", "status": "in_progress",
  "revision_id": "uuid|null", "meta_data": {}, "failure_acknowledged_at": null
}
```
`GET /jobs/{job_id}` adds progress fields: `total_tasks`, `completed_tasks`, `in_progress_tasks`,
`failed_tasks`, `pending_tasks`, `progress_percentage`, `tasks_completed[]`,
`tasks_in_progress[]`, `tasks_failed[]`, `tasks_pending[]` — poll this for any progress UI.

## 6. Tasks — ⚠️ path differs from what you might expect

Read-only; tasks are the individual steps inside a job.

| Method & Real Path | Purpose |
|---|---|
| `GET /tasks/jobs/{job_id}/tasks` | List tasks for a job. **Not** `/jobs/{job_id}/tasks` — see Verified state. |
| `GET /tasks/{task_id}` | One task's status. |
| `PATCH /tasks/{task_id}` | System-only — worker reports task status. |

```json
{ "id": "uuid", "job_id": "uuid", "type": "extractor", "priority": "medium", "status": "completed", "description": "…", "meta_data": {} }
```
Prefer `?expand=tasks` on the job/job-list call over a separate request when you just need task
status alongside the job.

## 7. Revisions

A revision is a saved version of a section's draft.

| Method & Path | Purpose |
|---|---|
| `GET /projects/{project_id}/revisions?revision_status=completed&section_type=results` | List revisions for a project (mounted on `projects.py`, not `revisions.py`). |
| `POST /revisions` | Generic create — lower-level than `manual-draft` below. |
| `GET /revisions/{revision_id}` | One revision. |
| `PATCH /revisions/{revision_id}` | Update status/`origin_description`. |
| `DELETE /revisions/{revision_id}` | Soft delete. |
| `POST /projects/{project_id}/revisions/manual-draft` | Upload a hand-edited draft as a new revision (multipart: `parent_revision_id` + `draft_file`). |

```json
{
  "id": "uuid", "project_id": "uuid", "project_section_id": "uuid", "job_id": "uuid|null",
  "parent_revision_id": "uuid|null", "major_version": 1, "minor_version": 0,
  "status": "completed", "origin": "generated", "origin_description": null
}
```

**Revision assets — the actual content.** Typed getters (what the frontend normally uses):

| Method & Path | Purpose |
|---|---|
| `GET /revisions/{revision_id}/assets/config` | Config used to generate this revision. |
| `GET /revisions/{revision_id}/assets/evaluation` | Evaluation result. |
| `GET /revisions/{revision_id}/assets/draft?ext=json\|html` | Draft content. |
| `GET /revisions/{revision_id}/assets/citation` | List citations in the draft. |
| `GET /revisions/{revision_id}/assets/citation/{citation_id}` | One citation's detail. |
| `GET /revisions/{revision_id}/assets/citation/{citation_id}/download` | Presigned URL to the citation's source (PDF page/table image). |
| `GET /revisions/{revision_id}/export?expiration=3600` | Presigned URL to download the export. |

Plus generic (lower-level, not in most summaries of this API):
`GET /revisions/{revision_id}/assets`, `POST /revisions/{revision_id}/assets`,
`GET/PATCH/DELETE /revisions/{revision_id}/assets/{asset_id}`.

Citation shapes:
```json
{ "type": "text", "id": "c1", "page": 4, "source_text": "…", "has_source_file": true }
{ "type": "table", "id": "t1", "label": "Table 2", "page_start": 5, "page_end": 5, "has_source_file": true }
```

## 8. Feedback

Mounted separately, at `/revisions/{revision_id}/feedbacks` (own `feedbacks_router`, not part of
`revisions.py`).

| Method & Path | Purpose |
|---|---|
| `POST /revisions/{revision_id}/feedbacks` | `{ "category": "draft_quality", "sentiment": "like", "comment": "optional" }` |
| `GET /revisions/{revision_id}/feedbacks` | List. |
| `GET /revisions/{revision_id}/feedbacks/{feedback_id}` | One. |
| `PATCH /revisions/{revision_id}/feedbacks/{feedback_id}` | Update. |
| `DELETE /revisions/{revision_id}/feedbacks/{feedback_id}` | Remove. |

`category`: `draft_quality` \| `citation_quality` \| `extraction_quality` \| `other`.
`sentiment`: `like` \| `neutral` \| `dislike`.

## 9. Config Templates

`/configs` — reusable, user-saved generation configs, scoped per section type.

| Method & Path | Purpose |
|---|---|
| `POST /configs` | Save a template: `{ "name": "…", "section_type": "results", "data": {...DraftConfig} }`. |
| `GET /configs?section_type=results&project_id=` | List → `{ "default_template": {...}, "templates": [...] }`. |
| `GET /configs/{config_id}` | Full template detail. |
| `DELETE /configs/{config_id}` | Delete a user-saved template (system defaults can't be deleted). |

## 10. Agent Cache (system-only)

`/agent-cache` — internal dedup cache for expensive agent steps, called by UDP-Celery. Not for
frontend use, listed for completeness: `POST /agent-cache`, `GET /agent-cache/lookup?task_type=&input_hash=`.

## Still unverified — not found on either branch checked so far

- `POST /projects/{project_id}/assets/files/retry` — retry failed file extraction for specific
  `project_asset_ids`. Not found on `ai-edit-bug` or `feat/one-solution-v1`.
- `DELETE /projects/{project_id}/assets/{asset_id}/tables/{table_id}` — delete one extracted
  table from a Table Index asset. Not found on either branch.
- The "reject language change once a draft exists" rule (the field itself is real — see Jobs/
  Projects sections above and Verified state).

## What NOT to do

- Don't call `/api/v1/projects/{project_id}/jobs` expecting job creation/listing — the real path
  is `/api/v1/jobs/projects/{project_id}/jobs`.
- Don't call `/api/v1/jobs/{job_id}/tasks` expecting the task list — the real path is
  `/api/v1/tasks/jobs/{job_id}/tasks`.
- Don't assume `?search=` filtering works on any list endpoint except `GET /projects` — see the
  okra-kit skill; even there it's branch-dependent.
- Don't implement or document pin/unpin, job-retry, file-retry, or per-table delete as
  "already working" (or "unbuilt") on a given branch without first grepping that branch's own
  `src/fdm/routers/*.py` — every one of these has already been proven to differ between
  `ai-edit-bug` and `feat/one-solution-v1` in this check.
- Don't assume the project `language` field doesn't exist — it does on `feat/one-solution-v1`.
  Do still build the draft-guard validation rule as new work if asked; it's not implemented on
  any branch checked so far.
