---
name: django-transactions-jobs
description: >
  Data integrity under concurrency and reliable background work in Django on PostgreSQL:
  transaction.atomic, select_for_update, conditional updates, F() expressions and database
  constraints to prevent lost updates, double processing and invalid state transitions; short
  transactions with no slow external calls under locks; on_commit for post-commit dispatch (and
  its delivery limits) and an outbox only when dispatch must be durable; background jobs with
  the project's existing queue (Celery, Django tasks or custom) — job states, retries/backoff,
  timeouts, duplicate delivery, idempotent tasks, progress, cancellation and observability. Use
  when code changes state that two requests or workers could change at once, when adding or
  reviewing a task/job/cron, or when debugging duplicates, lost updates, deadlocks or stuck jobs.
---

# Transactions, concurrency and background jobs

## 1. Inspect

1. **What runs concurrently**: web workers and threads, task workers, cron or management
   commands, retries. Assume any handler can run twice at once.
2. **The project's job system**: `grep -rniE "celery|shared_task|@task|django_tasks|dramatiq|rq|apscheduler|management/commands/cron"`.
   Read one existing job end to end: dispatch → queue → worker → status updates → retry and
   failure handling. Integrate with that system; don't add a new one.
3. **Versions**: Django, Celery (or other queue), broker type (Redis, SQS, RabbitMQ). Delivery
   and retry semantics depend on them.
4. **The invariant**, in one sentence: "an order can be cancelled once, only from pending/paid";
   "a job's result is written exactly once"; "stock never goes below 0".

## 2. Pick the mechanism (simplest that holds the invariant)

| Problem | Mechanism |
|---|---|
| Counter / balance arithmetic | `F()` update: `filter(pk=..).update(stock=F("stock") - n)`, plus a `CheckConstraint(stock__gte=0)` |
| One-shot state transition | Conditional update: `updated = filter(pk=.., status__in=ALLOWED).update(status=NEW)`; `updated == 0` → conflict (409) |
| Read, decide in Python, then write several rows | `transaction.atomic()` + `select_for_update()` on the rows being decided on |
| "Only one may exist" / dedup | `UniqueConstraint` (+ `condition=` for partial), catch `IntegrityError` — not check-then-insert |
| Work queue claimed by many workers | `select_for_update(skip_locked=True)` on pending rows |
| Fail fast instead of waiting on a lock | `select_for_update(nowait=True)` → handle `DatabaseError` |
| Side effect after the data is committed (email, task, webhook) | `transaction.on_commit(...)` |
| Side effect that **must** happen if the commit happened | Outbox row in the same transaction + relay/sweeper |

Rules:

- Keep transactions short. No HTTP calls, file processing, or task results awaited while
  holding row locks. Do the slow work first or after, and lock only for the decision and the write.
- Lock rows in a consistent order (e.g. by pk) to avoid deadlocks. Expect and retry
  serialization or deadlock errors where they're possible.
- `on_commit` callbacks run after the outermost atomic block commits (immediately if no
  transaction is open) and are dropped on rollback. They aren't part of the transaction, so
  a crash between commit and callback loses them. Use `robust=True` (Django 4.2+) so
  one failing callback doesn't break the others.
- Choose an outbox only when losing a dispatch is unacceptable *and* nothing else (a periodic
  sweep of rows in a pending state) already recovers it.

Patterns with code (including the order-cancel example):
[references/concurrency-patterns.md](references/concurrency-patterns.md).
Job design, retries, idempotency, Celery specifics:
[references/background-jobs.md](references/background-jobs.md).

## 3. Verify

- **Test on PostgreSQL**, not SQLite. Locking, `skip_locked`, `nowait` and isolation behave differently.
- Commit behaviour (`on_commit`, task dispatch after commit): `TestCase.captureOnCommitCallbacks(execute=True)`.
- Real concurrency (two connections racing for a lock): `TransactionTestCase` with two
  threads, each closing its DB connection at the end. Assert that exactly one wins.
- Tasks: call the task function directly for logic. Test the duplicate-delivery case (run it
  twice and assert one effect), the retryable failure, and the permanent failure.
- State the invariant and run its adversarial case (`invariant-verification`).

## Output

1. **Invariant**: one sentence, and how concurrent access could break it today.
2. **Mechanism chosen**, and why it's the simplest that holds.
3. **Changes**: files, plus any migration (constraints) and its locking impact.
4. **Verification**: tests run (and on which database), and the race or duplicate case.
5. **Limits**: what still isn't guaranteed (e.g. "dispatch is best-effort; a crash after commit
   drops the email — sweep or outbox if that matters").

## Example prompts

- "Make order cancellation safe when two requests hit `POST /orders/{id}/cancel/` at the same time."
- "Our nightly job sometimes processes the same invoice twice — find out why and make it idempotent."
- "Add a retry-safe background export: 202 with a job id, progress, cancel, and no duplicate files on retry."
- "Is it safe to send this webhook inside `transaction.atomic()`? Fix it if not."

## Sources

- Transactions, `atomic`, `on_commit`, savepoints: https://docs.djangoproject.com/en/stable/topics/db/transactions/
- `select_for_update`: https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update
- `F()` and race conditions: https://docs.djangoproject.com/en/stable/ref/models/expressions/#avoiding-race-conditions-using-f
- Constraints: https://docs.djangoproject.com/en/stable/ref/models/constraints/
- Testing commit callbacks: https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.TestCase.captureOnCommitCallbacks
- PostgreSQL explicit locking: https://www.postgresql.org/docs/current/explicit-locking.html
- Celery tasks (retries, acks_late, idempotency): https://docs.celeryq.dev/en/stable/userguide/tasks.html
