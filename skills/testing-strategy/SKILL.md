---
name: testing-strategy
description: >
  Decision guide for what kind of test a change needs (unit, broker-mode integration, or perf/SLO)
  across fdm-be and udp-celery, plus writing conventions for each — including fixture-naming and
  in-memory-fake techniques worth adopting, and testcontainers flagged as an unadopted option. Use
  when adding or reviewing tests, or deciding whether a change needs more than a unit test.
---

# Testing Strategy — fdm-be / udp-celery

## Step 1 — decide what kind of test this change needs

| Change touches... | Test needed |
|---|---|
| Router/service/repository logic, pure functions | Unit test (direct mode) |
| A Celery task's interaction with the broker (routing, retries, ack timing) | Broker-mode test (`--via-broker`) |
| Anything on the critical path in `fdm-perf-test`'s SLO table (UDP e2e, draft generation, upload, create project) | Also run/check the Locust perf suite — see Step 3 |
| A task's idempotency or retry behaviour under `acks_late=True` | Unit test AND broker-mode test — direct mode won't catch double-ack bugs |

If unsure, default to unit test first (cheapest, fastest feedback), then ask "would this bug only show up with a real broker or under load?" — if yes, add the other layer too.

---

## Step 2 — writing conventions (unit + broker-mode)

- One behaviour per test function — don't test multiple things together
- Naming: `test_<function>_<scenario>_<expected_outcome>`
  e.g. `test_create_project_duplicate_name_raises_conflict`
- Use `AsyncMock` for async dependencies
- Mock at the boundary — mock repos in service tests, mock services in router tests
- All shared fixtures go in the existing `conftest.py` — never create a new one
- Use `pytest-asyncio` for async tests

### Fixture technique worth adopting (checked against agent-harbor's python-test skill, MIT)

- Verified: `fdm-be/tests/conftest.py` and `udp-celery/tests/unit/conftest.py` today only have
  *structural* mock fixtures (`mock_revision_repo`, `mock_assets_repo`, ...) — none named for a
  *business state* (e.g. `project_active`, `revision_draft`). When a test needs several variants
  of the same entity, a semantic fixture (named for the state it represents, not the mock it
  wraps) reads better than building that state inline per test, and a shared-field change only
  needs updating in one place. Add these alongside the existing structural mocks, don't replace
  them — structural mocks are still right for repo/service boundaries.
- For a repository interface mocked repeatedly across many tests, an in-memory fake (a small
  class satisfying the same interface, backed by a dict) is occasionally more useful than
  `Mock(spec=...)` — it actually round-trips data instead of returning whatever was stubbed, so
  it catches save/find mismatches a bare mock can't. Reach for it only when a test is genuinely
  exercising save→find round-trip logic, not as a default replacement for mocking.
- **testcontainers is not used anywhere in either repo** — `tests/integration` is excluded from
  the default run (`norecursedirs` in `pyproject.toml`) and relies on the developer's own
  docker-compose services already being up (`postgres-fdm` on 5433, per `env-mapping`). Spinning
  up ephemeral containers per test run would remove that manual dependency and could run in CI —
  flagging this as a real option, not proposing it unprompted: it's a new dependency plus a CI
  change (see `deps-doctor`), not something to add incidentally while writing one test.

### udp-celery: direct vs. broker mode

- **Direct mode (default):** `aws-vault exec developer -- uv run pytest tests/`
  Calls task functions directly — fast, debug-friendly, no broker needed. Use for normal task-logic tests.
- **Broker mode:** `aws-vault exec developer -- uv run pytest tests/ --via-broker`
  Full integration via RabbitMQ (requires running broker + worker). Use when the test needs to verify actual routing, retry, or `acks_late` ack-timing behaviour — direct mode calls the function in-process and can't catch bugs that only appear with a real broker round-trip.
- Tests use the `mode` fixture in `conftest.py` to switch between the two — don't hand-roll a separate fixture.

### Common pytest flags

| Flag | Use |
|---|---|
| `-x` | Stop on first failure |
| `-v` | Verbose output |
| `-s` | Don't capture stdout |
| `-k "pattern"` | Run only matching test names |
| `--tb=short` | Shorter tracebacks |
| `--cov=src --cov-report=term-missing` | Coverage with missing lines |

---

## Step 3 — does this need a perf/SLO check, not just a test?

Ask: does this change touch a pipeline listed in the SLO table? (UDP extraction, draft generation, asset upload, project creation, or anything in the request path for those.)

If yes:
- Run the Locust suite: `fdm-be/tests/perf/stress_test.py` (`locust -f tests/perf/stress_test.py --headless --users 20 --spawn-rate 2`)
- Validate the run itself is trustworthy first with `tests/perf/check_smoke.py` (confirms metric collection, no OOM, no rate-limit throttling skewing results) before trusting the p95 numbers
- Compare against the actual SLO targets — **the authoritative thresholds live in the `fdm-perf-test` skill, section 6, not duplicated here.** Check that skill directly rather than trusting a stale copy of the numbers.
- A regression here blocks merge even if unit/broker tests pass — SLO breach is its own failure category

If the change is unrelated to those pipelines, a unit/broker test is sufficient — don't run the full Locust suite for every PR.

---

## Known open gaps (carry these caveats when writing new tests)

- udp-celery has two open TODOs relevant to test design:
  - `qa_be_base_url` param is slated for rename to something generic (`callback_base_url`) — don't hardcode assumptions about that name in new tests
  - Async pool migration (gevent) and memory fixes are pending — don't write tests that assume current pool behaviour is final
