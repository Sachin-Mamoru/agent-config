# PostgreSQL investigation for Django apps

## Reading a plan

```python
print(qs.explain())                                  # estimate only, doesn't run the query
print(qs.explain(analyze=True, buffers=True))        # RUNS the query — read-only queries only
```

(PostgreSQL 18 includes buffer stats automatically with ANALYZE. For DML, wrap it in
`BEGIN; EXPLAIN ANALYZE ...; ROLLBACK;` in psql, never on shared data.)

Look for, in order:
1. **Estimated vs actual rows** far apart → stale statistics (`ANALYZE table;`) or a
   correlation the planner can't see.
2. **Seq Scan** on a large table with a selective filter → missing or unusable index.
3. **Nested Loop** with a large outer side and an inner scan per row → missing index on the join key.
4. **Sort** spilling to disk (`external merge`) → `ORDER BY` without a matching index, or `work_mem`.
5. **Buffers: shared read** high → data isn't cached; I/O-bound.

Plans differ between a 1k-row dev DB and production. Test plan-sensitive changes on
realistic volume, or reason from production's `pg_stat_statements` if the team has it.

## Indexes

- Index what you filter, join and sort on, in that order of importance. Composite index column
  order: equality columns first, then the range/sort column.
- Django: `Meta.indexes = [models.Index(fields=["tenant", "-created_at"], name=...)]`;
  partial: `models.Index(fields=[...], condition=Q(deleted_at__isnull=True), name=...)`;
  `GinIndex`/trigram for `icontains`/full-text (`django.contrib.postgres`).
- Every index slows writes and costs disk. Don't add one without a query that uses it.
- FKs get an index automatically in Django (`db_index=True` default on `ForeignKey`).
- Uniqueness belongs in a constraint (`UniqueConstraint`), not an app-level check. See
  `db-constraint-design`.

## Migrations on large tables

| Operation | Risk on a big, busy table | Safer approach |
|---|---|---|
| `CREATE INDEX` | Blocks writes for the duration | `AddIndexConcurrently` (`django.contrib.postgres.operations`) in a migration with `atomic = False` |
| `ADD COLUMN` with a non-volatile default (PG 11+) | Fast, metadata only | Fine |
| `ADD COLUMN` with a volatile default, or changing a column type | Full table rewrite under an exclusive lock | Add nullable, backfill in batches, then add constraint |
| `ADD CONSTRAINT` (FK/CHECK) | Validates all rows under lock | Add as `NOT VALID`, then `VALIDATE CONSTRAINT` separately (RunSQL) |
| `NOT NULL` on existing column | Full scan under lock | CHECK `NOT VALID` → validate → set NOT NULL (PG 12+ uses the check) |
| Data migration over many rows | Long transaction, locks, replication lag | Batched updates; a management command for very large backfills |

Old code keeps running against the new schema during a deploy, so schema changes must be
backward compatible with the previous release (expand → migrate → contract).

## Locks

```sql
SELECT pid, wait_event_type, wait_event, state, now() - xact_start AS xact_age, left(query, 120)
FROM pg_stat_activity WHERE datname = current_database() ORDER BY xact_age DESC NULLS LAST;

SELECT pid, pg_blocking_pids(pid) AS blocked_by, left(query, 120)
FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

Long-running `idle in transaction` sessions hold locks and block vacuum. In Django code,
they usually come from slow work (HTTP calls, file processing) inside `transaction.atomic()`.

## Connections

- Each Django process or thread holds its own connection. Gunicorn workers × threads + Celery
  concurrency + cron processes must fit under `max_connections` with headroom.
- `CONN_MAX_AGE` reuses connections per process (plus `CONN_HEALTH_CHECKS`). Django 5.1+
  has native psycopg pooling via `OPTIONS["pool"]`. Check the installed version before
  recommending it.
- PgBouncer in transaction mode: disable server-side cursors (`DISABLE_SERVER_SIDE_CURSORS = True`),
  avoid session-level state (`SET`, advisory session locks, prepared statements).

Sources: https://www.postgresql.org/docs/current/using-explain.html ,
https://www.postgresql.org/docs/current/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY ,
https://www.postgresql.org/docs/current/sql-altertable.html#SQL-ALTERTABLE-NOTES ,
https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW ,
https://docs.djangoproject.com/en/stable/ref/contrib/postgres/operations/#concurrent-index-operations ,
https://docs.djangoproject.com/en/stable/ref/models/indexes/ ,
https://docs.djangoproject.com/en/stable/ref/databases/#persistent-connections ,
https://docs.djangoproject.com/en/stable/ref/databases/#connection-pool
