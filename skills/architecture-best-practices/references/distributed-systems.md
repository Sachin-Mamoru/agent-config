# Distributed Systems Patterns

Deep-dive companion to principles.md §3 (Kleppmann) and §5 (Newman/Cockcroft). Use when the design involves multiple services, async messaging, or consistency questions.

## Consistency models — pick deliberately, not by default

| Model | Guarantee | Cost | When it fits |
|---|---|---|---|
| Strict serializability | Total order, as if single-threaded | Highest latency, lowest availability under partition | Financial transactions, inventory decrements where overselling is unacceptable |
| Snapshot isolation | Consistent point-in-time view per transaction | Moderate | Most transactional DB workloads (Postgres default-ish) |
| Read-committed | No dirty reads, but reads can differ across the same transaction | Lower | General CRUD where perfect consistency isn't business-critical |
| Eventual consistency | Converges eventually, no guarantee on timing | Lowest latency, highest availability | Caches, search indexes, read replicas, activity feeds, "likes" counts |

The failure mode to watch for: code implicitly assuming a stronger guarantee than the underlying store actually provides (e.g., reading from a replica immediately after writing to the primary and expecting to see the write).

## PACELC in practice
- **If Partitioned**: choose Availability (keep serving, risk staleness) or Consistency (refuse requests until partition heals).
- **Else (normal operation)**: choose Latency (respond fast, maybe from a local/cached copy) or Consistency (round-trip to confirm the latest state).
Most systems spend 99.9% of their time in "Else" — so the latency/consistency trade-off in the normal case usually matters more day-to-day than the partition behavior, even though partition behavior gets more airtime in theory discussions.

## Idempotency patterns
- **Idempotency keys**: client generates a unique key per logical operation (e.g., `Idempotency-Key` header); server stores which keys have been processed and returns the cached result for a repeat, rather than reprocessing. Essential for payment/order creation endpoints.
- **Natural idempotency**: design the operation so repeating it is safe by construction — e.g., "set status to SHIPPED" is naturally idempotent; "increment shipped count by 1" is not.
- **At-least-once + idempotent consumer** is the realistic target for message processing (Celery tasks, queue consumers) — don't chase exactly-once delivery as a transport guarantee; build idempotency into the handler instead.

## The outbox pattern (solving the dual-write problem)
Problem: you need to write to your DB *and* publish an event, and both need to happen atomically — but a DB and a message broker can't share a transaction.
Solution: write the event into an "outbox" table in the same DB transaction as the business write. A separate poller/CDC process reads the outbox and publishes to the broker (e.g., RabbitMQ), then marks it published. If the publish fails, retry — the event is durably stored and the retry is naturally idempotent-safe since publish failures don't roll back the (already-committed) main transaction.

## Saga pattern (distributed transactions without 2PC)
When a business transaction spans multiple services (e.g., reserve inventory → charge payment → schedule shipment), each with its own DB:
- **Choreography**: each service publishes an event on completion; the next service reacts. Simple, but the overall flow is implicit — hard to see the whole process in one place.
- **Orchestration**: a central saga orchestrator explicitly calls each step and handles compensation. Easier to reason about and debug, at the cost of a new central component.
- **Compensating transactions**: since there's no distributed rollback, each step needs an explicit "undo" (refund payment, release inventory reservation) that the saga triggers on failure partway through.

## Event-driven architecture: choreography vs orchestration trade-off
Choreography scales better organizationally (services don't need to know about each other) but makes the end-to-end flow hard to trace and debug — a classic case of the "distributed monolith" risk if overused for tightly-coupled business processes. Orchestration centralizes complexity but keeps it visible. For genuinely independent side-effects (e.g., "send a welcome email when a user signs up"), choreography is fine. For a business-critical multi-step transaction, lean toward orchestration or at minimum very good distributed tracing.

## Backpressure & queue design
- An unbounded queue is a memory leak waiting for a traffic spike, not a resilience feature (Nygard's antipattern list).
- Prefer bounded queues with an explicit policy for what happens when full: reject (fail fast, protects the system) vs block the producer (fail safe, protects data, risks cascading slowness upstream).
- For task queues specifically (Celery/RabbitMQ), pair with the AWS/K8s reference for autoscaling consumers based on queue depth (KEDA) rather than fixed worker counts.

## Distributed tracing is not optional past 2 services
Once a request can cross more than one service boundary, you need correlation IDs propagated through logs and traces (W3C traceparent header or equivalent) or debugging a production incident becomes archaeology. This should be designed in at the same time as the service split, not bolted on after the first unresolvable incident.
