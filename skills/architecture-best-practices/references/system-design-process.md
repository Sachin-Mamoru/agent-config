# Greenfield System Design Process

Use when the ask is "design a system for X," "should this be a new service," or "how should I architect this."

## Step 1 — Requirements before architecture
Resist the urge to jump to technology choices. Establish, explicitly:
- **Functional requirements**: what must it do?
- **Non-functional requirements / quality attributes**: what matters more — latency, throughput, consistency, cost, time-to-market, team familiarity? These usually conflict with each other, and naming the priority order up front prevents circular debates later.
- **Constraints**: team size, existing stack, deadline, budget, compliance requirements. A "textbook best" architecture that ignores a 2-person team's operational capacity is not actually the best architecture for that team.
- **Scale, realistically, not hypothetically**: current load, and a *defensible* growth projection — not "what if we go viral." Design for ~10x current scale, not 1000x, unless there's genuine evidence for it (Yagni applies to scale planning too).

## Step 2 — Identify the actual bounded contexts (Evans/DDD lens)
- What are the core domain concepts, and where do their meanings actually diverge across the business? (see principles.md §2)
- This — not "how many services should we have" — is the real question. Service boundaries should follow domain boundaries, not the other way around.

## Step 3 — Decide the deployment topology, and justify it explicitly
Default posture: **start with a modular monolith** unless there's a concrete, already-known reason not to (Newman's guidance — see principles.md §5). Justifications that are actually sufficient:
- Different parts of the system need to scale independently by a wide margin (e.g., a synchronous API vs. a batch processing pipeline).
- Different parts need independent deployment cadence (e.g., a stable core vs. a rapidly-iterating feature team).
- A genuine bounded-context boundary with different consistency/ownership needs.
- Regulatory/compliance isolation requirements.

Justifications that are usually *not* sufficient on their own: "microservices are modern," "this could theoretically scale differently one day," "it'll be cleaner." If none of the concrete justifications apply, recommend the monolith and say so directly — pushing back here is one of the most valuable things a good architect does, because the microservices default is culturally strong but often expensive to walk back from.

## Step 4 — Data architecture
- Identify system of record for each entity. No two systems should both consider themselves authoritative for the same data.
- Choose consistency model per use case, not globally (Kleppmann lens — see principles.md §3). Payment state probably needs strong consistency; a "last seen online" timestamp doesn't.
- Decide sync vs async explicitly for cross-boundary communication: synchronous (REST/gRPC) for request/response where the caller needs an immediate answer; async (queue/event) where the caller can proceed without waiting, or where you want to decouple producer/consumer scaling and availability.

## Step 5 — Design for failure from the start (Nygard lens)
Don't treat reliability patterns as a "phase 2" concern — retrofitting timeouts, circuit breakers, and idempotency onto a system already in production is far more expensive than designing them in from the start. See references/distributed-systems.md and principles.md §4.

## Step 6 — Write it down as an ADR
Any non-trivial, hard-to-reverse decision (Type 1, per Bezos framing) should get a short Architecture Decision Record: context, options considered, decision, consequences (including the costs, not just the benefits). See `adr-template.md`. This is cheap insurance against relitigating the same decision in six months without the original context.

## Step 7 — Sanity-check against Conway's Law
Does the proposed architecture assume collaboration patterns between teams that don't actually happen? If the design requires two teams that rarely sync to co-evolve a shared interface constantly, expect friction — either change the design to reduce that coupling, or flag the organizational dependency explicitly as a risk.

## Anti-pattern to actively guard against: resume-driven architecture
Choosing a technology or pattern because it's interesting/new/CV-building rather than because it's the best fit for the actual constraints. Ask: would this same choice survive if no one would ever know which technology was used internally? If the honest answer is "no, I want to use X to learn it," that's a legitimate reason to negotiate with the team (learning has value) — but it should be named as such, not disguised as a purely technical recommendation.
