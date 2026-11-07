---
name: django-testing
description: >
  Write and run tests for Django / DRF code, and debug failures, within the repo's existing
  setup (pytest-django or Django's unittest runner): API tests for permissions, validation,
  business rules and edge cases; query-count guards against N+1 regressions; TestCase vs
  TransactionTestCase vs captureOnCommitCallbacks for commit and locking behaviour; mocking
  external boundaries, not the code under test; reproduce-first bug fixing; and an exact report
  of which checks ran and which couldn't. Use when adding or reviewing tests for a Django
  change, reproducing or fixing a bug in a Django app, or when a Django test fails or is flaky.
---

# Django / DRF testing and debugging

## 1. Inspect the existing setup (copy it, don't invent one)

- Runner: `pytest.ini`/`pyproject.toml [tool.pytest.ini_options]` with `DJANGO_SETTINGS_MODULE`
  → pytest-django; otherwise `manage.py test` (unittest). Check how CI runs it, in Docker or
  with a `--settings` flag, and with which database. Tests must run on the same database engine
  as production (PostgreSQL) whenever locking, JSON, array or full-text behaviour matters.
- Base classes and helpers: grep the test tree for the project's `TestCase` subclasses,
  factories/fixtures, API-client helpers, query-count helpers, and S3/Sentry/email mocks.
  Use them, and don't add factory_boy/model_bakery or new fixtures files if the project has its own.
- Naming and layout: mirror the module under test (`tests/views/test_orders.py` ↔
  `views/orders.py`), and use the project's class and method naming.
- Fast reruns: `--keepdb` / `--reuse-db`, run one module, `-x`/`--failfast`.

## 2. Write the tests the change needs

| Change | Tests |
|---|---|
| Endpoint / permission | Matrix: anonymous, authenticated-no-access, other tenant (expect the project's 404 vs 403), owner, admin. One `subTest`/parametrize row each. |
| Validation | Each invalid input → 400 with the right field key; one valid case; read-only fields ignored on input |
| Business rule / state transition | Allowed transitions succeed; each disallowed one → the project's conflict response; state unchanged afterwards |
| List endpoint | Query-count guard with ≥ 2 parents × ≥ 2 children, so an N+1 shows; ordering and pagination stable |
| Commit side effects (`on_commit`, task dispatch) | `with self.captureOnCommitCallbacks(execute=True) as callbacks:` (pytest-django: `django_capture_on_commit_callbacks`); assert the callback/task ran with the right id, and not on rollback |
| Locking / races | `TransactionTestCase` + threads on PostgreSQL (see `django-transactions-jobs`) |
| Task | Call the function directly; duplicate delivery; transient vs permanent failure |
| Migration (data) | Migrate to the previous state, create rows, migrate forward, assert; and backwards if reversible |

Rules:

- **Mock boundaries, not the unit under test**: HTTP clients, storage, email, queues, clocks
  (`timezone.now`). Patch where the name is *looked up* (`myapp.services.requests.post`), and
  assert the call's arguments, not just that it was called.
- **Assert behaviour, not implementation**: status code + body + resulting DB state.
- Query-count assertions are for concrete regressions (N+1 on lists, a hot path), not every
  test. Prefer an upper bound or the project's helper over brittle exact counts on complex views.
- Deterministic data: no reliance on default ordering, wall-clock time, or random ids.
- `setUpTestData` for read-only fixtures shared across a class (fast); `setUp` for per-test state.

## 3. Debugging (reproduce → isolate → fix → prove)

Follow `systematic-debugging`. Django specifics:

1. Reproduce as a failing test first, at the lowest layer that shows it.
2. Read the full traceback, then the SQL: `CaptureQueriesContext`, or log `django.db.backends` at DEBUG.
3. Usual suspects: queryset cache reuse or staleness (`refresh_from_db()`), signals,
   `Meta.ordering`, a missing tenant scope, `update()` skipping `save()`, timezone-naive datetimes,
   `TestCase` hiding commit behaviour, test-order dependence (run the single test alone and in
   reverse order: `--reverse` / `-p no:randomly`).
4. Fix the root cause in the shared function, then rerun the failing test and its neighbours.

## 4. Report exactly what ran

```
Ran:     <exact command> → <N passed, M failed> (database: postgres via docker compose)
Added:   tests/...::TestX::test_y — fails before the fix, passes after
Not run: <check> — <reason, e.g. needs MFA / service not running / migration tests are a separate job>
```

Never write "tests pass" without the command and the result from this session.

## Example prompts

- "Write the permission matrix tests for the new `cancel` action, using our existing test helpers."
- "This test passes alone and fails in the full suite — find the leak."
- "Add a query-count guard to the orders list so the N+1 we just fixed can't come back."
- "Prove that the export task isn't dispatched when the transaction rolls back."

## Sources

- Testing tools (`TestCase`, `TransactionTestCase`, `assertNumQueries`, `captureOnCommitCallbacks`):
  https://docs.djangoproject.com/en/stable/topics/testing/tools/
- Test runner options (`--keepdb`, `--parallel`, `--reverse`): https://docs.djangoproject.com/en/stable/ref/django-admin/#test
- DRF testing (`APIClient`, `force_authenticate`): https://www.django-rest-framework.org/api-guide/testing/
- pytest-django fixtures (`django_capture_on_commit_callbacks`, `django_assert_max_num_queries`):
  https://pytest-django.readthedocs.io/en/latest/helpers.html
- `unittest.mock` "where to patch": https://docs.python.org/3/library/unittest.mock.html#where-to-patch
