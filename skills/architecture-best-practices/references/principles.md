# Core Principles, By Theme

Each principle is attributed to where it's most associated. These are distillations of publicly known bodies of work (books, talks, blogs) — not verbatim quotes. When applying one, name the principle and the trade-off, not just the conclusion.

## Table of contents
1. Coupling, cohesion & maintainability (Fowler)
2. Domain-driven design (Evans, Vernon)
3. Distributed systems trade-offs (Kleppmann)
4. Designing for failure (Nygard)
5. Microservices judgment (Newman, Cockcroft)
6. Flow, DevOps & organizational design (Kim, Forsgren/Accelerate, Conway)
7. Simplicity & complexity (Ousterhout, Hickey, Beck)
8. Cost & reversibility (Bezos, Fowler's Yagni)

---

## 1. Coupling, cohesion & maintainability — Martin Fowler

- **Coupling is the enemy, cohesion is the friend.** A module should have one reason to change, and changes to one module shouldn't ripple through unrelated ones. When reviewing code, ask: "if I change this, what else breaks?" — a large blast radius signals bad coupling regardless of how clean the code looks locally.
- **Refactoring is a discipline, not a rewrite.** Small, behavior-preserving steps with tests as a safety net beat big-bang rewrites. If someone proposes "let's just rewrite this," ask what's preventing incremental strangler-fig style migration instead (see anti-patterns.md).
- **Yagni ("You Aren't Gonna Need It")**: don't build for a hypothetical future requirement. Speculative generality is a smell, not virtue. This directly supports the meta-principle: prefer the reversible, minimal thing.
- **Technical debt is a metaphor for a real trade-off**, not an excuse. Deliberate, informed debt (ship now, pay down later, and actually schedule the payback) is different from inadvertent debt (didn't know better) — the former is a legitimate strategy, the latter is a risk to flag.
- **The strangler fig pattern**: replace a legacy system incrementally by routing traffic to the new system feature-by-feature, letting the old system's footprint shrink until it can be switched off. Preferred over rewrites for anything business-critical.

## 2. Domain-driven design — Eric Evans, Vaughn Vernon

- **Start from the domain model, not the database schema or the framework.** The core insight of DDD: software should model the business's actual language and concepts (the "ubiquitous language"), not translate awkwardly between business terms and technical ones.
- **Bounded contexts**: a large domain should be split into contexts where a term means one specific thing. "Order" in the billing context isn't the same shape as "Order" in the fulfillment context — don't force one shared model across both. This is often the actual, principled reason to split a service, rather than "microservices are modern."
- **Aggregates and invariants**: define clear consistency boundaries — a cluster of objects that must be consistent together, with one entry point (the aggregate root). Don't let external code reach into an aggregate's internals; this is a common source of hidden coupling.
- **Anti-corruption layer**: when integrating with a legacy system or a third-party API with a poor model, wrap it in a translation layer so its awkwardness doesn't leak into your clean domain model.

## 3. Distributed systems trade-offs — Martin Kleppmann (*Designing Data-Intensive Applications*)

- **Every distributed system choice is a trade-off, not a free win.** CAP theorem is a simplification; the more practically useful frame is **PACELC**: if there's a Partition, trade off Availability vs Consistency; Else (no partition), trade off Latency vs Consistency. Most systems spend most of their time in the "Else" branch, so latency-vs-consistency in the normal case matters as much as partition behavior.
- **Consistency models exist on a spectrum**: strict serializability → snapshot isolation → read-committed → eventual consistency. Pick the weakest model that the business logic can actually tolerate — stronger consistency always costs latency and availability. Don't default to "strong consistency everywhere" without naming the cost.
- **Idempotency is not optional in distributed systems.** Any operation that can be retried (and over an unreliable network, everything can be retried) needs an idempotency key or natural idempotent design, or duplicate processing becomes a production incident.
- **The outbox pattern** solves the "dual write problem" (writing to a DB and publishing an event must be atomic): write the event to an outbox table in the same transaction as the business data, then a separate process publishes from the outbox. Prevents the classic bug of publishing an event for a transaction that then rolls back.
- **Exactly-once delivery doesn't really exist across a network** — design for at-least-once delivery plus idempotent consumers instead of chasing exactly-once as a guarantee.

## 4. Designing for failure — Michael Nygard (*Release It!*)

- **Assume every dependency will fail, and design the blast radius, not just the happy path.** Nygard's stability patterns:
  - **Circuit breaker**: stop calling a failing dependency after a threshold, to avoid cascading failure and to give the dependency room to recover.
  - **Bulkheads**: isolate resource pools (thread pools, connection pools) per dependency so one slow downstream doesn't starve resources needed for everything else.
  - **Timeouts everywhere**: any network call without an explicit timeout is a latent incident. "It usually responds fast" is not a timeout strategy.
  - **Fail fast vs fail safe**: decide deliberately whether a component should reject requests immediately when unhealthy (fail fast, protects the system) or degrade gracefully (fail safe, protects the user) — this should be a conscious choice per component, not an accident.
- **The stability antipatterns to actively watch for**: unbounded retries without backoff, unbounded queues (memory exhaustion under load), and synchronous chains of synchronous calls (a slow leaf service stalls the entire call chain).

## 5. Microservices judgment — Sam Newman, Adrian Cockcroft

- **Microservices are an organizational and scaling tool, not a default architecture.** Newman's core message (often lost in industry hype): the justification for splitting a service should be an independent deployability or independent scaling need, or a genuine bounded-context boundary — not "microservices are best practice."
- **Cockcroft's framing**: microservices trade complexity in the small (individual services are simple) for complexity in the large (the system as a whole is a distributed system with all its inherent difficulty — network calls, partial failure, eventual consistency, distributed tracing needs). A team should only make this trade when the benefits (independent scaling, independent deployment cadence, fault isolation) outweigh the operational cost.
- **The premature microservices trap**: splitting before the domain boundaries are well understood produces a **distributed monolith** — many of the deployment/operational costs of microservices with none of the decoupling benefit, because services still have to change in lockstep. Newman's advice: start with a well-modularized monolith; split when a specific, articulable pain (scaling, team boundary, deployment cadence) demands it.
- **Data ownership per service**: each service should own its data exclusively; no service should reach into another's database directly. Shared databases across services are one of the most common sources of accidental coupling in a "microservices" system that behaves like a monolith anyway.

## 6. Flow, DevOps & organizational design — Gene Kim (*The Phoenix Project*, *Accelerate*), Conway's Law

- **The Three Ways (Kim)**: (1) optimize flow left-to-right through the system, (2) create fast feedback loops right-to-left, (3) build a culture of continuous experimentation and learning. Most organizational dysfunction in engineering traces back to violating one of these — work piling up in a queue (flow), problems discovered too late (feedback), or punishing failure so no one takes a risk (learning culture).
- **DORA / Accelerate metrics (Forsgren, Humble, Kim)**: the four keys that empirically correlate with high-performing engineering orgs are deployment frequency, lead time for changes, change failure rate, and time to restore service. These are useful diagnostic questions when reviewing an existing system's *process*, not just its code: "how long does it take to get a one-line fix to production?" often reveals more than a code review does.
- **Conway's Law**: "organizations design systems that mirror their own communication structure." If a proposed architecture requires tight collaboration between two teams that rarely talk, expect the architecture to degrade toward the org chart regardless of the diagram. When reviewing a proposed service split, always sanity-check it against team structure — this is one of the most underused but highest-value review questions.

## 7. Simplicity & complexity — John Ousterhout (*A Philosophy of Software Design*), Rich Hickey ("Simple Made Easy"), Kent Beck

- **Ousterhout's "deep modules"**: the best modules have a simple interface hiding substantial implementation complexity. The worst modules are "shallow" — their interface is nearly as complicated as their implementation, so they add indirection without hiding anything. When reviewing an abstraction, ask: does this interface actually hide complexity, or just relocate it?
- **Complexity is either essential or accidental** (a framing going back to Fred Brooks, sharpened by Hickey): essential complexity comes from the problem itself and can't be removed, only managed; accidental complexity comes from tooling, architecture, or process choices and *can* be removed. Good architectural review distinguishes which kind of complexity you're looking at before proposing a fix.
- **Hickey's "simple vs easy"**: simple means "not intertwined" (objectively about the structure), easy means "familiar / close at hand" (subjective, about the person). A familiar but tangled framework can be "easy" while being deeply not-simple. Don't mistake familiarity for good design.
- **Beck / XP tradition**: "make it work, make it right, make it fast" — in that order. Premature optimization for performance before correctness, or premature abstraction before a second real use case exists, are both violations of this sequencing.
- **Rule of three**: don't abstract/generalize after one use case, and be cautious even after two. Wait for a third concrete need before extracting the general-purpose version — the first two data points are rarely enough to know the right shape of the abstraction.

## 8. Cost & reversibility — Jeff Bezos ("Type 1 vs Type 2 decisions"), Fowler's Yagni

- **Type 1 (one-way door) vs Type 2 (two-way door) decisions**: Type 1 decisions are hard/costly to reverse and deserve heavy deliberation; Type 2 decisions are cheap to reverse and should be made quickly by whoever's closest to the problem, without escalating. Misclassifying a Type 2 decision as Type 1 (excessive process for a reversible choice) is a common organizational failure mode, as is the reverse (treating a genuinely hard-to-reverse choice, like a data model or a public API contract, too casually).
- **Public APIs and data schemas tend to be Type 1** (hard to reverse once external consumers depend on them) — deserve more upfront design rigor than internal implementation details, which are usually Type 2.
- This is the practical engine behind the meta-principle in SKILL.md: always ask which door you're walking through before deciding how much analysis the decision deserves.
