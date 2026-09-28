# Architecture Decision Record (ADR) Template

Use for any Type 1 (hard-to-reverse) decision per Bezos framing (principles.md §8) — public API contracts, data model choices, service boundary decisions, core infra choices, or anything a future engineer would ask "why did we do it this way?" about.

## Template

```markdown
# ADR-<number>: <short decision title>

**Status**: Proposed | Accepted | Superseded by ADR-<n>
**Date**: <date>
**Deciders**: <names/roles>

## Context
What problem are we solving? What constraints (team size, timeline, existing stack, scale) shaped the space of options? What's the current pain, if any, driving this decision now?

## Options considered
1. **Option A** — one-line description
2. **Option B** — one-line description
3. **Option C** — one-line description (include "do nothing" / status quo as an option if genuinely viable)

## Decision
Which option was chosen, stated plainly in one or two sentences.

## Rationale
Why this option, specifically against the runner-up — not a generic list of the winner's virtues, but the actual trade-off that tipped it. Reference the specific quality attribute (from Requirements) that mattered most.

## Consequences
**Benefits** (what we gain)
- ...

**Costs / trade-offs accepted** (what we're deliberately giving up — this section is not optional; if it's empty, the analysis is incomplete)
- ...

**Follow-up required** (migrations, monitoring to add, a re-evaluation date if this is meant to be revisited)
- ...
```

## Worked example

```markdown
# ADR-014: Use RabbitMQ + Celery for async report generation instead of inline synchronous generation

**Status**: Accepted
**Date**: 2026-06-15
**Deciders**: Sachin M. (backend), team lead

## Context
Report generation for the /api/v1/reports endpoint currently runs synchronously inside the request handler and takes 8-45 seconds depending on data volume, causing client timeouts and blocking worker capacity for unrelated requests during generation. Current stack already runs Celery + RabbitMQ for other background work, and KEDA autoscaling is already configured on the cluster.

## Options considered
1. Keep synchronous generation, increase request timeout and worker count to compensate.
2. Move generation to an existing Celery queue, return a job ID immediately, client polls/gets notified on completion.
3. Move to a separate serverless (Lambda) pipeline outside the main cluster.

## Decision
Option 2 — move report generation to a dedicated Celery queue (`reports`, separate from existing `default` and `notifications` queues), with KEDA scaling workers on that queue's depth.

## Rationale
Option 1 doesn't fix the underlying problem, just delays it, and increasing timeouts risks worse resource exhaustion under concurrent report requests (unbounded blocking work, per Nygard's stability antipatterns). Option 3 was rejected mainly on team-familiarity and operational-cost grounds (new deployment target, new observability integration) relative to the marginal benefit over Option 2, given Celery/RabbitMQ/KEDA are already in place and well understood by the team.

## Consequences
**Benefits**
- Request handler returns in <200ms regardless of report size; no more client-side timeouts.
- Report generation failures are isolated to the `reports` queue/worker pool (bulkhead) and don't affect other Celery task types.
- Scales independently via KEDA based on `reports` queue depth.

**Costs / trade-offs accepted**
- Client-facing API contract changes from synchronous (return the report) to asynchronous (return a job ID; client polls or is notified) — this is a breaking change for existing API consumers and needs a versioned rollout (see api-design.md).
- New failure mode to handle: what happens if a report job fails partway (partial report generated)? Requires an explicit idempotent retry design (see distributed-systems.md), not just "retry the whole task."
- Slightly higher end-to-end latency for small/fast reports that would've completed synchronously in under a second — a minor UX regression for the simplest case, accepted as a reasonable trade for the majority of cases where reports are slow.

**Follow-up required**
- Add job-status polling endpoint and/or WebSocket notification.
- Add dead-letter handling and alerting for permanently-failed report jobs.
- Migration plan and deprecation window for existing synchronous API consumers.
```
