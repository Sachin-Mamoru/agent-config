---
name: django-orm-performance
description: >
  Measure-first performance work for Django ORM on PostgreSQL and the Python around it. Covers
  QuerySet evaluation and caching, N+1 diagnosis with real query counts, select_related /
  prefetch_related / Prefetch / annotate / aggregate (including join-multiplied aggregates),
  count/exists/len/iterator, EXPLAIN plans and indexes, large result sets, locks, connections,
  migration impact on big tables, and Python profiling (I/O- vs CPU-bound, threads vs asyncio vs
  processes, GIL and free-threaded builds). Use when an endpoint, command, task or query is slow,
  issues too many queries, times out, uses too much memory, or when reviewing ORM code, models,
  indexes or migrations for performance.
---

# Django ORM / PostgreSQL / Python performance

Rule zero: **measure, change one thing, measure again.** No optimisation without a number
before and after, such as a query count, a plan, a timing or a memory peak.

## 1. Inspect

1. Versions: Django, psycopg, the PostgreSQL server (`SELECT version();`), the Python build
   (`python -VV`). Version-specific advice depends on all of them.
2. Reproduce the slow path with realistic data volume. Ten rows hide N+1s, and query plans
   change with table size and statistics.
3. Measure what it does:
   - **Query count and SQL**: the project's query-count helper, `assertNumQueries` in a test,
     `django.test.utils.CaptureQueriesContext(connection)` in a shell (stable, but not in the
     official docs), or django-debug-toolbar/silk if installed. (`connection.queries` is only
     populated when `DEBUG=True`.)
   - **Plan**: `print(qs.explain(analyze=True, buffers=True))` on PostgreSQL. ANALYZE executes
     the query, so never run it with writes against shared data.
   - **Python time**: `cProfile`/`pstats` around the call, or `py-spy` against a running process.
     Look at where the time goes before choosing a fix.
4. Classify the problem: too many queries (N+1), one slow query (plan/index), too much data
   (rows/columns/memory), lock waits, connection exhaustion, or Python CPU.

## 2. Fix (smallest change that addresses the measured cause)

| Measured cause | Typical fix |
|---|---|
| N+1 on FK / one-to-one | `select_related(...)` in `get_queryset()` |
| N+1 on reverse FK / M2M | `prefetch_related(...)`; `Prefetch("items", queryset=..., to_attr=...)` to filter/order/limit the related set |
| Per-row counts/sums in Python | `annotate(Count(...), Sum(...))` / `aggregate(...)`; `Subquery`/`OuterRef` when combining several multi-valued relations |
| Loading rows only to test existence or count | `.exists()` / `.count()` (but reuse the cache if the queryset is evaluated anyway) |
| Wide rows not needed | `.only()` / `.defer()` / `.values()` — careful: touching a deferred field costs one query per row |
| Huge result set in memory | `.iterator(chunk_size=...)` or keyset batches by `pk`; never `list()` a million rows |
| Seq scan on a selective filter | Index matching the filter/order (`Meta.indexes`, partial/conditional index); confirm with the plan |
| Write races or lock waits | See `django-transactions-jobs` |
| Python CPU in the request | Profile; move it out of the request only if latency matters (a worker doesn't make CPU work faster) |

Details and traps: [references/queryset-evaluation.md](references/queryset-evaluation.md)
(caching, `len` vs `count`, prefetch traps, aggregation duplicates),
[references/postgres-investigation.md](references/postgres-investigation.md) (plans, indexes,
locks, connections, migrations on large tables),
[references/python-performance.md](references/python-performance.md) (profiling, concurrency
model, GIL).

## 3. Verify

- Re-run the same measurement and report both numbers: queries 61 → 4, p95 or plan cost, rows scanned.
- Add a regression guard where it protects something concrete: a query-count assertion on the
  list endpoint (`assertNumQueries` or the project's helper) that would fail on an N+1 with
  more rows. Seed at least two related rows per parent, or the N+1 won't show up.
- New index or constraint: show the plan using it; check the migration's locking impact first.
- Run the touched tests and the project's checks.

## Output

1. **Measurement before**: the numbers and where they came from.
2. **Cause**: one sentence, with the evidence (SQL snippet or plan node).
3. **Change**: the files and the specific ORM or index change.
4. **Measurement after**, plus the guard test added.
5. **Trade-offs and follow-ups**: for example a denormalised counter, a new index's write cost,
   or a migration needing a maintenance window, listed separately.

## Example prompts

- "`GET /orders/` takes 2s with 50 items — find the N+1 and add a test that would catch it again."
- "This report sums line items per customer and the totals look doubled — explain and fix."
- "Is the new index in this migration used, and is it safe to run on a 40M-row table?"
- "Profile `generate_invoice_pdf` and tell me whether threads, processes or a worker would help."

## Sources

- QuerySet evaluation, caching and API: https://docs.djangoproject.com/en/stable/ref/models/querysets/ ,
  https://docs.djangoproject.com/en/stable/topics/db/queries/#caching-and-querysets
- Database access optimisation: https://docs.djangoproject.com/en/stable/topics/db/optimization/
- Aggregation (incl. combining multiple aggregations): https://docs.djangoproject.com/en/stable/topics/db/aggregation/
- PostgreSQL EXPLAIN and indexes: https://www.postgresql.org/docs/current/using-explain.html ,
  https://www.postgresql.org/docs/current/indexes.html
- Python profilers: https://docs.python.org/3/library/profile.html
