# Python & FastAPI Architecture Patterns

## Layering (avoid the "fat router" antipattern)
A common FastAPI-specific smell: business logic living directly in route handler functions. Prefer explicit layers:
- **Router/endpoint layer**: HTTP concerns only — parsing request, calling a service function, shaping the response. No business logic.
- **Service/use-case layer**: the actual business logic, framework-agnostic (doesn't import `fastapi`). This is what makes business logic testable without spinning up the HTTP framework, and portable if you ever need to call the same logic from a Celery task or CLI script instead of an HTTP request.
- **Repository/data-access layer**: DB queries isolated behind an interface, so the service layer doesn't know if it's Postgres, Mongo, or a mock in tests.

This mirrors Fowler's coupling/cohesion principle directly: a router that also contains business logic has more than one reason to change (HTTP contract changes AND business rule changes), which is a cohesion violation even though it "still works."

## Dependency injection as the seam for testability
FastAPI's `Depends` system is the natural place to inject: DB sessions, current authenticated user, external API clients, feature flags/config. In tests, override these with `app.dependency_overrides` rather than monkeypatching imports — it's more explicit and less brittle across refactors.

## Async pitfalls specific to Python
- **Blocking calls inside `async def`**: the single most common performance bug in FastAPI codebases. A sync DB driver (e.g., `psycopg2` instead of `asyncpg`/`psycopg` async mode), `requests` instead of `httpx.AsyncClient`, or `time.sleep` instead of `asyncio.sleep` inside an async route blocks the whole event loop — meaning *other unrelated requests* on that worker stall too, not just the slow one. Always audit: is every I/O call in this async path actually non-blocking?
- **CPU-bound work doesn't belong in async handlers at all** — async concurrency helps with I/O-bound waiting, not CPU-bound computation. CPU-heavy work (image processing, ML inference, heavy serialization) should go to a background worker (Celery) or a thread/process pool executor, not inline in an async route.
- **Connection pool sizing**: async code can issue far more concurrent DB connections than sync code naturally would, since there's no thread limit gating concurrency. Make sure the DB connection pool size is deliberately set, not left at a framework default that assumes sync-style concurrency.

## Celery + RabbitMQ architecture
- **Task granularity**: tasks should be small and idempotent (see distributed-systems.md). A task that does five unrelated things is hard to retry safely — if step 3 of 5 fails, does re-running redo steps 1-2 harmfully?
- **Explicit retry policy per task**: `max_retries` + exponential backoff (`retry_backoff=True`), not infinite retries. Pair with a dead-letter queue (or Celery's equivalent — a failure-handling task/queue) so permanently-failing tasks are visible and don't retry forever.
- **Task timeouts**: set both a soft time limit (raises an exception inside the task, allowing cleanup) and a hard time limit (kills the worker process) — a runaway task without a hard limit can silently pin a worker slot indefinitely, starving the queue.
- **Idempotency at the task level**: since RabbitMQ/Celery gives at-least-once delivery (a task can be redelivered after a worker crash mid-execution), task bodies must tolerate being run twice. Common pattern: check-then-act on a status field, or use a DB-level unique constraint as a guard.
- **Routing and queue segregation**: don't put a slow, resource-heavy task (e.g., report generation) on the same queue as latency-sensitive tasks (e.g., sending a password-reset email) — one queue's backlog delays the other's tasks. Use separate queues + separate worker pools (Celery's `task_routes`) so they scale and fail independently — this is the bulkhead pattern (Nygard) applied to task queues.
- **KEDA-based autoscaling**: scale Celery worker pods based on RabbitMQ queue depth (KEDA's RabbitMQ scaler) rather than CPU/memory — queue depth is a much more direct signal of "there's a backlog" than worker CPU, which may look idle even with a growing backlog if tasks are I/O-bound.

## Testing strategy
- **Unit tests** for the service layer (pure business logic, no framework, no network) — should be fast and numerous.
- **Integration tests** for the repository layer against a real (test) database — catches ORM/query bugs unit tests with mocks would miss.
- **Contract tests** for the API layer (using FastAPI's `TestClient`/`httpx.AsyncClient`) — verify the HTTP contract (status codes, schema shape) without necessarily re-testing business logic already covered at the service layer.
- **Race-condition tests for Celery tasks**: at minimum, test what happens if the same task runs twice (idempotency check) — this is the failure mode most likely to actually occur in production and least likely to be caught by a straightforward test suite.

## Configuration & secrets
- Twelve-factor config: environment-driven config, not hardcoded values or config files checked into the repo with real secrets. Pydantic's `BaseSettings` (or `pydantic-settings`) is the idiomatic FastAPI-ecosystem way to do this with validation.
- Fail fast on missing/invalid config at startup, not on first use deep in a request path — a misconfigured app should refuse to start, not serve broken requests intermittently.
