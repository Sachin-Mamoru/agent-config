# Architecture / Design / PR Review Checklist

Use this when the ask is "review this," "what's wrong with this," "is this a good design," or when reviewing a colleague's PR at an architectural (not just line-by-line) level.

## Step 1 — Understand intent before critiquing form
Before flagging anything, be able to state in one sentence: what business or technical problem is this change solving? If you can't, ask, or infer it from context (ticket, PR description, surrounding code) before reviewing. Critiquing a design against a problem you've guessed wrong is worse than not reviewing at all.

## Step 2 — Run through these lenses in order

### A. Correctness & failure modes (Nygard lens)
- Does every external call (HTTP, DB, queue, cache) have an explicit timeout?
- What happens if this dependency is slow, not just down? (slow failures are more dangerous than hard failures — they hold resources)
- Are retries bounded, with backoff and jitter? Unbounded retry = thundering herd risk.
- Is this operation idempotent if retried? If not, is there an idempotency key?
- Is there a circuit breaker or equivalent for a dependency that could cascade failure upstream?
- Bulkheads: does one slow/failing dependency share a resource pool (thread pool, DB connection pool) with unrelated critical paths?

### B. Coupling & cohesion (Fowler lens)
- If this module's internals change, what has to change elsewhere? Is that blast radius proportionate to what the change is?
- Is there a clean interface, or is calling code reaching into internals (breaking encapsulation)?
- Does this PR do one thing? (a PR/module doing three unrelated things is a cohesion smell at the change level, not just the code level)
- Is this the minimal change that solves the stated problem (Yagni), or does it add speculative flexibility for hypothetical future needs?

### C. Data & consistency (Kleppmann lens)
- Where's the source of truth for this data? Is it duplicated anywhere, and if so, how do the copies stay consistent (and what happens when they don't)?
- If this involves a DB write + event/message publish, is there a dual-write problem? (see outbox pattern in distributed-systems.md)
- What consistency model does this actually need? Is the code assuming stronger consistency than what's actually guaranteed (e.g., assuming synchronous read-after-write against an eventually-consistent store)?

### D. Ownership & boundaries (Evans/Newman lens)
- Does this change reach across a service or bounded-context boundary in a way that creates hidden coupling (e.g., one service's code directly querying another service's database)?
- If this introduces a new service/module boundary: is it justified by an independent scaling/deployment need or a genuine domain boundary, or is it split "because microservices"? A split without a concrete justification is worth pushing back on.

### E. Observability & operability
- Can someone on-call diagnose a failure in this without reading the source code? (structured logging, meaningful error messages, metrics/traces)
- Are there metrics/alerts for the failure modes identified in section A, or does this only get discovered when a customer complains?
- Is there a rollback path? For infra/deploy changes, is it a Type 1 or Type 2 decision (Bezos framing) — and does the rigor of the review match that?

### F. Testing
- Do tests cover the failure paths identified above, not just the happy path?
- For concurrency-sensitive code (async, Celery tasks, shared state): is there a test for the race condition, or just the sequential case?

## Step 3 — Frame feedback as trade-offs, not verdicts
Instead of "this is wrong," state: "this optimizes for X but costs Y — was that the intended trade-off?" This is both more accurate (most architecture decisions really are trade-offs) and more useful to the recipient, since it invites them to either confirm the trade-off was deliberate or reconsider it.

## Step 4 — Prioritize findings
Not everything found is equally important. Rank using something like:
1. **Correctness/data-loss risk** — blocking, must fix before merge/ship
2. **Reliability risk under failure** (missing timeout, unbounded retry, no circuit breaker) — should fix, can sometimes ship with a tracked follow-up if there's time pressure and the blast radius is genuinely contained
3. **Coupling/maintainability concern** — worth raising, rarely blocking on its own
4. **Style/idiom preference** — mention once, don't relitigate

## Quick red-flag list (fast pass for time-constrained reviews)
- No timeout on a network call
- Retry loop with no backoff or max attempts
- A service directly reading/writing another service's database
- A "temporary" workaround with no ticket/TODO tracking its removal
- New abstraction/interface introduced for a single current use case (violates rule of three)
- Synchronous chain of >2 network hops in a user-facing request path with no async/queue option considered
- PR description doesn't explain *why*, only *what*
