# Named Anti-Patterns & Smells

Use this as a fast lookup when something "feels wrong" but you need to name why.

## Distributed monolith
Multiple deployed services that still have to be deployed together or in a specific order, because they share a database, share a synchronous call chain with no fallback, or have implicit contract coupling that isn't enforced by anything. You get all the operational cost of microservices (network calls, partial failure, deployment complexity) with none of the benefit (independent deployability). **Root cause**: services split before bounded contexts were well understood (see system-design-process.md §2-3). **Fix**: identify the actual coupling (shared DB? synchronous dependency chain?) and either genuinely decouple it or acknowledge the services should be merged back.

## Big ball of mud
No discernible architecture — code grows by accretion, with no clear layering or boundaries, until every change risks unpredictable breakage elsewhere. **Root cause**: no one owns architectural integrity over time; each incremental change was locally reasonable but the aggregate has no coherent shape. **Fix**: strangler-fig incremental extraction (Fowler) of clear modules/boundaries, rather than a rewrite (see principles.md §1).

## God object / god service
A single class, module, or service that knows about and touches too much of the system — often started small and kept absorbing "just one more thing" because it was the path of least resistance. **Symptom**: it appears in the dependency graph of almost everything. **Fix**: identify the distinct responsibilities via the cohesion lens (Fowler) and split along those lines, not arbitrarily.

## Chatty API / N+1
A client (frontend, or a service calling another service) makes many small sequential requests to assemble what's conceptually one piece of data, instead of one request that returns it directly. Classic ORM version: looping over a list and querying a related object per iteration instead of a single joined/batched query. **Cost**: each round-trip pays full network latency, and this compounds badly across a service boundary or a slow network. **Fix**: batch/aggregate endpoints, `JOIN`/eager-loading at the ORM level, or a tailored BFF layer (see react-frontend.md, api-design.md).

## Premature microservices
Splitting a system into services before the domain boundaries or scaling needs are actually known, "because that's the modern way to build things." Produces the distributed monolith above, or a system where the team spends more time on service-to-service plumbing than on the actual business logic. **Fix**: default to a well-modularized monolith; split only for a concrete, named reason (see system-design-process.md §3).

## Resume-driven architecture
Choosing a technology, pattern, or level of complexity because it's interesting to the engineer or good for their CV, rather than because it fits the problem's actual constraints. Not inherently illegitimate (learning has real value to a team) but dangerous when it's disguised as a purely technical recommendation rather than named honestly. See system-design-process.md's closing note.

## Golden hammer
Using one familiar tool/pattern for every problem regardless of fit (e.g., "everything is a REST API," "everything goes through Kafka," "every list needs Redux") because it's the tool the team already knows, not because it's the best fit. Related to Hickey's "simple vs easy" distinction (principles.md §7) — familiarity is being mistaken for correctness.

## Vendor/framework lock-in without a plan
Deeply coupling business logic to a specific framework's or cloud provider's APIs, without an anti-corruption layer (Evans, principles.md §2), such that migrating later (or even upgrading a major version) requires touching business logic throughout the codebase. Not always wrong to accept (sometimes the lock-in is a fine trade for velocity) — but should be a conscious Type-1-decision choice (Bezos framing), not an accident of not having thought about it.

## Cargo-culting "best practices"
Applying a pattern (microservices, CQRS, event sourcing, hexagonal architecture) because it's associated with "good engineering" in the abstract, without the underlying problem that pattern actually solves being present. Every pattern in this skill has a *specific* problem it solves and a *specific* cost — a recommendation that can't name both is a red flag, including when Claude itself is the one making the recommendation.

## Analysis paralysis vs recklessness — two failure modes on either end
- **Analysis paralysis**: treating a Type 2 (easily reversible) decision with Type 1 rigor — weeks of design debate over a config value or an internal implementation detail that could be changed in an afternoon if wrong.
- **Reckless velocity**: treating a Type 1 (hard to reverse) decision — a public API contract, a core data model, a foundational infra choice — with Type 2 casualness, shipping without an ADR or real trade-off discussion.
Both are miscalibrations of the same underlying judgment call (Bezos framing, principles.md §8); a good architect's actual skill is classifying which type of decision they're facing, quickly and correctly.
