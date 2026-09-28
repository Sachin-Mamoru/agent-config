# okra_kit — Generic Query Engine (fdm-be)

## Verified state — ⚠️ this flips between branches, re-check before trusting it

**okra_kit itself is not identical across fdm-be branches** — it's an in-progress, in-repo
toolkit and different feature branches carry different versions of it. Confirmed by direct
comparison: on branch `ai-edit-bug` @ `e185254` (checked 2026-09-15), free-text search was
**not implemented at all**. On branch `feat/one-solution-v1` @ `61bea9c` (re-checked same day,
after being told the wrong branch was used the first time), search **is fully implemented**.
Don't trust either finding for a branch you haven't personally checked — re-run the "how to
verify" grep below first.

**On `feat/one-solution-v1` (current known state)**:
- Real, in-repo package at `fdm-be/src/okra_kit/` (not a published PyPI package). Public exports
  are `QueryEngine` and `DataPipelineOrchestrator` (`okra_kit/__init__.py`).
- Wired into three repositories in fdm-be: `src/fdm/repositories/project_repository.py`,
  `src/fdm/repositories/app/jobs.py`, `src/fdm/repositories/app/project_assets.py`. Not used in
  udp-celery, qa-be, or core.
- **Free-text search is real**: `core/query/search.py` defines `QuerySearch` — a case-insensitive
  `ILIKE '%term%'` across whatever `search_fields` were configured, clauses `OR`'d together,
  wildcard characters in the user's input escaped via `escape_like()` so they're treated
  literally. `QueryEngine.__init__(table, metadata, dialect=..., search_fields=None)` accepts the
  param; `QueryContext`/`QueryParams` carry a `search` field wired through
  `adapters/fastapi/deps/query_context.py`. **But only `GET /projects` actually uses it** —
  `project_repository.py` is the only repository that passes `search_fields=("name",
  "description")` to its `QueryEngine(...)` call; `jobs.py` and `project_assets.py`'s
  repositories construct `QueryEngine(table, metadata_obj)` with no `search_fields`, so `?search=`
  is silently a no-op on jobs/project-assets list endpoints (falls through `QuerySearch.apply`'s
  `if not search or not self.search_fields: return query` guard) — it won't error, it just won't
  filter anything.
- Everything else documented below — pagination, sorting, filtering, forward/reverse expand,
  inline expand filters, related-field filtering, field projection, grouping, metrics,
  time-series bucketing, scoping, error types, and validation limits — was spot-checked against
  the real source (`constants.py`, `core/models/query.py`, `core/query/engine.py`,
  `core/query/group_by.py`, `core/query/scope.py`, `core/policies/scope.py`,
  `core/exceptions.py`, `adapters/fastapi/deps/query_context.py`) on both branches and matches
  on both — the search feature is the one thing that differs between them.

**How to re-verify which state your branch is in**: `grep -n "search_fields" src/okra_kit/core/query/engine.py`
— if that's empty, search isn't implemented on your checkout; if it shows up as a constructor
param, check `grep -rn "search_fields=" src/fdm/repositories/` to see which specific resources
actually enable it.

## Big picture

```
Frontend URL query params
   → Router: get_query_context() (FastAPI dep) → QueryContext → QueryParams.from_context()
   → Repository: QueryEngine.build_query(params, user_id=..., additional_scope_rules=[...])
   → DB executes qr.query (+ qr.count_query for pagination)
   → Service: DataPipelineOrchestrator(model=ResponseModel, params=params).assemble(total, rows, qr)
   → Clean paginated JSON response
```

**Query-build pipeline order** (inside `QueryEngine.build_query`):
`scope → expand → filter → group_by → interval → metrics → order → pagination`
(no `search` stage — see the gap noted above).

**Data pipeline order** (inside `DataPipelineOrchestrator.assemble`):
`pagination → relation nesting → model validation → field projection → grouping`

## Query parameters (reference)

| Parameter | Default | Notes |
|---|---|---|
| `page` | `1` | 1-based |
| `page_size` | `10` | `0` = all, capped at `MAX_PAGE_SIZE=200` |
| `order_by` | `-created_at` | comma-separated columns, `-` prefix = descending |
| `expand` | none | comma-separated relation names, max `MAX_TOKENS=10` |
| `include_fields` | none | whitelist; mutually exclusive with `exclude_fields` |
| `exclude_fields` | none | blacklist |
| `metrics` | none | comma-separated `fn:column` (or `fn:N:column` for `percentile`), max 10 |
| `group_by` | none | comma-separated columns, **max 5** (enforced in `QueryContext._validate_group_by`, `max_tokens=5`) |
| `interval` | none | one of the time intervals below |
| `time_field` | `created_at` | column used for interval bucketing |
| `{column}` / `{column__op}` | — | dynamic filter; any query param not in the reserved set above is treated as a filter |
| `search` | — | free-text ILIKE across configured `search_fields` — **only enabled on `GET /projects`** as of this check; a no-op elsewhere. See Free-text search below and re-verify per branch. |

Reserved param names live in `RESERVED_PARAMS` (`adapters/fastapi/deps/query_context.py`); any
other query param on the request becomes a filter automatically. Use
`get_query_context_factory(extra_reserved=["your_param"])` instead of `get_query_context` when an
endpoint has a custom param (e.g. `include`) that must NOT be treated as a filter.

## Filter operators

`{column}__{operator}=value`, `eq` is the default when no `__operator` suffix is given.

| Operator | Meaning | Value shape |
|---|---|---|
| `eq` | `=` | single |
| `neq` | `!=` | single |
| `gt` / `gte` / `lt` / `lte` | `>` `>=` `<` `<=` | single |
| `contains` | `LIKE '%v%'`, case-sensitive | string |
| `icontains` | `ILIKE '%v%'` | string |
| `startswith` / `endswith` | `ILIKE 'v%'` / `ILIKE '%v'` | string |
| `include` / `exclude` | `IN (...)` / `NOT IN (...)` | comma-list |
| `isnull` | `IS NULL` / `IS NOT NULL` | `true`/`false` |

Multiple filters combine with `AND`. Max 20 filters per request (`MAX_FILTERS`).

## Free-text search (branch-dependent — see Verified state)

`search=<term>` — case-insensitive `ILIKE '%term%'` matched against whichever columns the
repository configured as `search_fields` when constructing its `QueryEngine`; matches across
those columns are `OR`'d together. Not a `column__operator` expression like other filters — it's
a single free-text term applied to a fixed, server-side-chosen column set. Wildcard characters
(`%`, `_`) the user types are escaped so they're literal, not SQL patterns. If a repository
didn't pass `search_fields`, or the term is empty, the parameter is silently ignored (no error).

```python
self.query_engine = QueryEngine(projects, metadata_obj, search_fields=("name", "description"))
```

As of this check, only `project_repository.py` does this — `GET /projects?search=climate` really
filters; `GET /projects/{id}/jobs?search=...` and the project-assets list endpoint do not.

## Relations

**Forward** (`?expand=project`): looks for `{relation}_id` on the table, resolves the target
table (tries plural forms), does a `LEFT JOIN`. On Postgres the joined columns are wrapped in
`json_build_object(...)`; SQLite/MySQL fall back to flat dot-notation, reassembled in Python by
`data_pipeline/relation_expander.py`.

**Reverse** (`?expand=tasks`): use the **exact table name** (usually plural — `tasks`, not
`task`). Requires the child table to have an FK back to the parent (`job_id` on `tasks`).
Builds a correlated `json_agg(...)` subquery; soft-deleted children (`deleted_at IS NOT NULL`)
are excluded automatically.

**Inline expand filters** — reverse relations only, not forward:
`?expand=tasks(status=completed,type__include=extract|validate)`. Inside the parentheses, `|`
separates list values (not `,`, since `,` already separates filter pairs at that level).

**Filtering on related data without expanding**:
- Forward: `?project__name__icontains=Research` → `LEFT JOIN` + `WHERE`.
- Reverse: `?task__status__eq=failed` → `EXISTS (SELECT 1 FROM tasks WHERE tasks.job_id = jobs.id
  AND tasks.status = 'failed')` — doesn't duplicate parent rows the way a join would.
- `include`/`exclude` on a related field treats the literal string `"null"` as "no related row
  exists" (FK is NULL), e.g. `?project_section__section_type__include=null,introduction`.

## Field projection

`include_fields` (whitelist) and `exclude_fields` (blacklist) are mutually exclusive —
using both raises `ConflictingParametersError`. Relation fields (marked
`json_schema_extra={"relation": True}` in the Pydantic response model) are auto-hidden unless
explicitly expanded. Nested projection uses dot notation: `exclude_fields=tasks.id,tasks.meta_data`.
When using `include_fields` with an expanded relation, the relation name itself must also be in
the top-level include list, or the whole relation gets dropped.

## Grouping vs. metrics

- `group_by` alone → Python-side grouping (`data_pipeline/grouper.py`): each result is
  `{key_columns..., "items": [...]}`, full rows preserved.
- `group_by` + `metrics` → SQL-level `GROUP BY` with aggregate `SELECT`; the row shape becomes
  `{key_columns..., "{col}_{fn}": value}`.

## Metrics

`metrics=fn:column` (comma-separated, max 10 tokens). Output column is always `{column}_{fn}`,
except `median` which is just `median`, and `percentile:N:column` → `{column}_p{N}`.

| Function | Needs numeric column? | PG-only? |
|---|---|---|
| `count`, `min`, `max`, `distinct_count` | no | no |
| `sum`, `avg`, `stddev`, `variance` | yes | no |
| `median`, `percentile:N:column` | yes | **yes** |

## Time-series bucketing

`interval={second\|minute\|hour\|day\|week\|month\|quarter\|year\|decade}` +
`time_field=<column>` (default `created_at`). Output bucket column is `{time_field}_{interval}`.
Dialect-specific SQL (`core/constants.py`): Postgres `date_trunc(...)`, SQLite `strftime(...)`,
MySQL `DATE_FORMAT(...)` — `quarter`/`decade` need custom expressions outside Postgres.

## Scoping (automatic, `core/policies/scope.py`)

Applied to every query, no caller action needed:
- Table has `deleted_at` column → adds `deleted_at IS NULL`.
- Table has `created_by` column → adds `created_by = :user_id`.

Extend with `additional_scope_rules=[ScopeRule("project_id", project_id)]` on `build_query(...)`
(this is how every current caller scopes to a parent resource — see Integration below). Disable
entirely with `disable_default_scopes=True` for admin-style views.

## Errors

Every `okra_kit` exception subclasses `ValueError` (`core/exceptions.py`) so existing
`except ValueError` handlers convert them to `HTTP 400` automatically — no new exception handling
needed when wiring in a new endpoint.

| Exception | When |
|---|---|
| `InvalidColumnError` | unknown column referenced |
| `InvalidFilterOperatorError` | unknown `__operator` |
| `InvalidExpandError` | unknown relation in `expand` |
| `InvalidMetricError` | malformed `fn:column` token |
| `InvalidIntervalError` | interval unsupported on this dialect |
| `ConflictingParametersError` | e.g. `include_fields` + `exclude_fields` together |

## Validation limits (`core/constants.py` + `core/models/query.py`)

| Limit | Value |
|---|---|
| `page_size` | 200 max, 0 = all |
| metric tokens | 10 |
| filters | 20 |
| `group_by` columns | 5 |
| `expand` tokens | 10 |
| field-name-list string length | 500 chars |

Validated in three layers: FastAPI `Query(...)` bounds → Pydantic `QueryContext` validators →
`QueryEngine` checking columns actually exist on the real table.

## Adding okra_kit to a new endpoint

Follow the pattern already used by `jobs.py` (router + `src/fdm/repositories/app/jobs.py` +
`src/fdm/services/jobs.py`) — copy that, don't reinvent it:

1. **Schema**: mark relation fields with `Field(default=None, json_schema_extra={"relation":
   True})` so they're hidden unless expanded.
2. **Repository**: `self.query_engine = QueryEngine(table, metadata_obj)`, optionally with
   `search_fields=("col1", "col2")` if this resource should support `?search=` (check whether
   your branch's `QueryEngine` even accepts this param first — see Verified state); in the list
   method, `qr = self.query_engine.build_query(params,
   user_id=self.user_id, additional_scope_rules=[ScopeRule("project_id", project_id)])`, then
   execute `qr.count_query` (if present) and `qr.query`.
3. **Service**: `DataPipelineOrchestrator(model=ResponseModel,
   params=params).assemble(total_count, rows, qr)`.
4. **Router**: `ctx: Annotated[QueryContext, Depends(get_query_context)]`, then
   `params = QueryParams.from_context(ctx)`. Use `get_query_context_factory(extra_reserved=[...])`
   instead if the endpoint has its own non-filter query params.

## What NOT to do

- Don't assume `?search=` works on every list endpoint — check the specific repository's
  `QueryEngine(...)` call for a `search_fields=` argument first; as of this check only
  `GET /projects` has it wired up.
- Don't assume `search_fields`/`QuerySearch` exist at all without checking your actual branch —
  this genuinely differs between fdm-be feature branches (confirmed: absent on `ai-edit-bug`,
  present on `feat/one-solution-v1`).
- Don't use inline expand filters (`expand=relation(...)`) on a forward relation — only reverse
  relations support them.
- Don't combine `include_fields` and `exclude_fields` in the same request.
- Don't assume this is usable outside fdm-be without first vendoring/publishing it — udp-celery,
  qa-be, and core don't currently depend on it.
