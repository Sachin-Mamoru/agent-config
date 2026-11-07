# Background jobs: reliable, idempotent, observable

Use the project's existing mechanism: Celery, Django's tasks framework, RQ or Dramatiq, a
DB-polling cron command, or a custom Redis queue. The design rules below hold for all of them.
The Celery notes apply only when Celery is what's installed.

## What a background worker does and doesn't buy

It moves work off the request path (latency, timeouts, retries, scheduling). It doesn't make
CPU work faster, and a queue adds failure modes: lost dispatch, duplicate delivery, stuck
jobs. If the work takes 200 ms and nothing calls an unreliable service, keep it in the request.

## Dispatching from a transaction

```python
with transaction.atomic():
    export = Export.objects.create(owner=user, status="pending")
    transaction.on_commit(lambda: run_export.delay(export.pk))   # never before commit
```

- Dispatch inside the transaction (without `on_commit`) means the worker can run before the
  row is committed and won't find it, or the transaction rolls back and the job runs anyway.
- Celery 5.4+ offers `task.delay_on_commit(...)` for Django (tasks based on `DjangoTask`). It
  wraps the same `on_commit` and returns no task id, so use `on_commit` directly if you need the id.
- Django 6.0+ tasks framework (`django.tasks`): `@task` + `.enqueue()`; the docs recommend
  `transaction.on_commit(partial(my_task.enqueue, ...))`. Django ships only development/testing
  backends (`ImmediateBackend` default, `DummyBackend`) and no worker, so production needs a
  third-party backend. Don't introduce it alongside an existing queue.
- `on_commit` isn't durable. If dispatch must not be lost, keep the row in `pending` and have
  a periodic sweep re-dispatch stale pending rows, or write an outbox row and relay it.

## Job resource and states

`pending → running → succeeded | failed | cancelled`, with `attempts`, `started_at`,
`finished_at`, `progress` (0–100 or step name), `error` (safe message) and `result` (or a
storage key). Transition with conditional updates (`filter(pk=.., status="pending").update(status="running")`)
so a duplicate delivery can't start the same job twice.

## Idempotent tasks — assume at-least-once delivery

Brokers redeliver (worker crash, `acks_late`, visibility timeout), and retries re-run the body.
Make running twice harmless:

- Claim the job with a conditional update. If 0 rows match, someone else has it or it's done,
  so return.
- Write results keyed by a stable id: an upsert or a unique constraint, and a deterministic storage key.
- External side effects: pass an idempotency key to the provider, or record "sent" in the DB
  before/after with a constraint.
- Pass ids to tasks, not model instances or large payloads, and re-read state inside the task.

## Retries, backoff, timeouts

- Retry only transient errors (timeouts, 5xx, connection errors). Validation and logic errors
  fail immediately.
- Bounded retries with exponential backoff and jitter. Record the final failure on the job row.
- Set a time limit per task. Use a soft limit to clean up, and a hard limit as a backstop.
- Celery: `autoretry_for=(TransientError,)`, `retry_backoff=True`, `retry_backoff_max`,
  `retry_jitter=True`, `max_retries` (`retry_backoff_max` defaults to 600 s);
  `soft_time_limit`/`time_limit` (soft raises `SoftTimeLimitExceeded`); `acks_late=True` +
  `task_reject_on_worker_lost=True` only for idempotent tasks. The latter can loop
  redeliveries, and newer Celery adds `task_retry_on_worker_lost` to cap them, so check the
  installed version. With Redis/SQS brokers, a task not acknowledged within the
  `visibility_timeout` (defaults: 1 h on Redis, 30 min on SQS) is redelivered. An ETA, countdown or
  retry delay longer than that timeout, or a task running longer than it, causes repeated execution.

## Progress and cancellation

- Progress: update the job row at coarse steps (not per item), with an `update()` on that row.
- Cancellation is cooperative: the API sets `status="cancel_requested"` (conditional update),
  and the task checks it between steps and stops cleanly. Revoking or killing a running task
  doesn't roll back its side effects. Define what "cancelled" means for partially written output.

## Observability

Log with the job id, attempt number and outcome. Expose queue depth and age of the oldest
pending job. Alert on jobs stuck in `running` past their time limit. A periodic sweeper that
marks those `failed` (or re-queues idempotent ones) closes the loop.

## Testing

- Call the task function directly for logic (or Celery's `task_always_eager` only if the project
  already uses it; it hides broker behaviour).
- Duplicate delivery: run the task twice for the same job, and assert one result and one side effect.
- Transient failure: mock the external boundary to fail once, and assert the retry path. Then
  fail permanently and assert the job ends `failed` with an error.
- Dispatch-after-commit: `captureOnCommitCallbacks()` and assert the task was queued with the
  job id, and not queued when the transaction rolls back.

Sources: https://docs.djangoproject.com/en/stable/topics/db/transactions/#performing-actions-after-commit ,
https://docs.djangoproject.com/en/stable/topics/tasks/ ,
https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying ,
https://docs.celeryq.dev/en/stable/userguide/tasks.html#automatic-retry-for-known-exceptions ,
https://docs.celeryq.dev/en/stable/userguide/workers.html#time-limits ,
https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html#visibility-timeout ,
https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html#trigger-tasks-at-the-end-of-the-database-transaction ,
https://docs.celeryq.dev/en/stable/faq.html#faq-acks-late-vs-retry
