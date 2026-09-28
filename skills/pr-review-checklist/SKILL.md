---
name: pr-review-checklist
description: >
  Checklist for reviewing PRs across fdm-be, udp-celery, and okra-kustomize. Covers architecture
  rules (router/service/repository layering), Helm values consistency, KEDA config correctness,
  configmap key safety, common mistakes, and higher-level architectural findings (coupling/
  cohesion, missing retry paths, schema-vs-workaround tradeoffs). Findings are reported as
  file/line/comment, written like an engineer explaining a real finding to a colleague, not a
  review bot. Use when reviewing or approving a PR.
---

# PR Review Checklist

---

## Two passes, not one: checklist + architecture

The checklists below catch the concrete, nameable stuff — layering violations, missing tests,
Helm drift. They won't catch a design that's correct on every individual line but wrong as a
whole: a handler quietly turning into a god function, an async dispatch with no recovery path,
a query standing in for a constraint. For anything beyond a trivial change, also run the diff
through `architecture-best-practices` (coupling/cohesion, bulkhead/failure isolation, outbox/
retry patterns, deep-module vs shallow-module) and say explicitly when a finding comes from that
lens rather than a checklist line — don't bury it as if it were just another checklist item.

Patterns worth naming specifically, because they keep recurring in this codebase:
- **An async dispatch (Celery, SQS, whatever) with no recovery path** if it fails between the DB
  commit and the actual send. Check whether the codebase already has a working sweep/retry
  pattern elsewhere (e.g. a `trigger_pending_*` job scan) that this should reuse instead of
  inventing a new, unrecoverable failure mode.
- **One handler accumulating unrelated side effects for different resource types** inside a
  shared try/except. Each new feature adding another `if type == X:` branch to the same function
  is the tell. Name the extraction (one hook per concern, each with its own error boundary)
  rather than just flagging the specific line that happens to trip over it.
- **A query working around a missing constraint** — scanning a JSONB field for what's really a
  foreign key, or a docstring that admits a check "narrows but doesn't close" a race. Name the
  schema-level fix even when applying it isn't in scope for this PR.

## How to report findings

- Give every finding as **file (linked) + line number(s) + comment**, in a table, so it can be
  pasted straight into GitHub as inline review comments. A finding that spans a whole function or
  pattern rather than one line goes in as a separate top-level PR comment instead of being forced
  onto a single line — say so explicitly rather than picking an arbitrary anchor line.
- Write the comment text like you're actually saying it to the PR author, not like a review bot
  generating a report. Say what you checked, not just what you suspect — "confirmed X by tracing
  Y" beats "this might cause X." No hedging preambles, no filler praise, no vague "consider
  refactoring this" — name the concrete failure scenario or the concrete fix.
- Full technical sentences are fine here — this is a different register from a Slack ping (see
  `chat-message-voice`, which covers chat cadence specifically, not this). What carries over from
  that skill is its hard "don't" list against AI-writing tells (banned vocabulary like "crucial"/
  "robust"/"testament", banned patterns like "not just X, it's Y", hedging openers like "it's
  worth noting") — that list is general-purpose, not chat-specific, and applies to review
  comments just as much.
- Distinguish "worth a discussion" from "confirmed bug" from "verified fine, no action needed" —
  don't flatten everything into one undifferentiated list of concerns.

---

## fdm-be PRs

### Architecture layer rules
- [ ] Routers only call services — never repositories directly
- [ ] `HTTPException` only raised in routers — never in services or repositories
- [ ] Services raise domain exceptions (e.g. `ObjectDoesNotExist`) — never `HTTPException`
- [ ] Repositories only do DB access — no business logic, no schema imports
- [ ] Errors logged with structured key=value context: `logger.error("msg", key=val, error=str(e))`

### API design
- [ ] Route decorator has `summary`, `description`, and `responses` (OpenAPI)
- [ ] Request body schemas suffixed `Request`, responses suffixed `Response`
- [ ] `status_code=201` for creation, `204` for delete-no-body
- [ ] Path params for identity, query params for filtering/pagination

### Schema versioning
- [ ] New code checks `schema_version` before processing revisions
- [ ] `schema_version=1` revisions treated as read-only (no refine/evaluate)
- [ ] New revisions created with the latest schema version

### Migrations
- [ ] Every new/changed UNIQUE index or constraint: state "two rows are duplicates when ___"
      and confirm every column that sentence names is in the key columns, not only in
      `postgresql_where` — see `db-constraint-design` (caught a real bug in
      `uq_project_assets_file_name`, where `file_type` was WHERE-only)
- [ ] Any app-level duplicate/conflict pre-check filters on exactly the same columns as the DB
      constraint's key, not a subset

### Tests
- [ ] New behaviour has a test — one behaviour per test function
- [ ] Test names follow: `test_<function>_<scenario>_<expected_outcome>`
- [ ] Shared fixtures added to existing `conftest.py` — never a new conftest
- [ ] Services mocked in router tests; repositories mocked in service tests

---

## udp-celery PRs

### Async patterns
- [ ] LanceDB uses `connect_async()` — never `connect_sync()`
- [ ] Polars: `lazyframe.collect_async()` — never `.collect()`
- [ ] Independent async calls use `asyncio.TaskGroup` — not `asyncio.gather()`
- [ ] `except* Exception as eg` used after TaskGroup — unwraps `ExceptionGroup` before propagating to Celery retry logic

### Celery task rules
- [ ] `acks_late=True` and `reject_on_worker_lost=True` on task classes
- [ ] `should_retry` in `FdmBaseTask` receives the raw exception type (not wrapped in `ExceptionGroup`)

### Helm values (if touching `charts/udp-celery/`)
- [ ] Change applied consistently across **all 4 env files** (development/staging/acceptance/production) unless intentionally env-specific
- [ ] `minReplicaCount`, `maxReplicaCount`, `pollingInterval`, `cooldownPeriod` make sense together
- [ ] `maxReplicaCount` ≥ expected peak concurrent tasks (N_users × tasks_per_user with headroom)

---

## okra-kustomize PRs

### Base vs overlay fix
- [ ] If fixing a bug, check whether it should be in `base/` (applies to all clients) or a specific overlay
- [ ] If fixing in base, verify **all overlays using that base** are still valid after the change
- [ ] Use `kustomize build kustomize/overlays/<env>/<client>/` locally to validate before merging

### ConfigMap safety
- [ ] New configmap keys referenced in deployments/env exist in the configmap
- [ ] Keys that may not exist in all overlays use `optional: true` in the secretKeyRef/configMapKeyRef
- [ ] No hardcoded secrets in configmaps — secrets go in K8s Secret objects

### Overlay consistency
- [ ] If adding a new overlay for one client, check if other clients need the same
- [ ] Image tag (`newTag`) updated correctly — matches the short SHA from the product repo CI
- [ ] Namespace in `kustomization.yaml` matches the expected namespace for that environment

---

## General (all repos)

- [ ] No `print()` statements — use structured logger
- [ ] No `assert False` — use proper exceptions
- [ ] No secrets committed — check for tokens, passwords, API keys
- [ ] `pre-commit` hooks pass (`uv run pre-commit run --all-files` for Python repos)
- [ ] No unnecessary dependencies added to `pyproject.toml`
- [ ] Branch is up-to-date with `develop` before merging
