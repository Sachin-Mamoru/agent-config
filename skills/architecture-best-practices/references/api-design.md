# API Design

## Style choice: REST vs GraphQL vs gRPC — pick by access pattern, not fashion
- **REST**: default choice for resource-oriented public/external APIs. Well-understood caching (HTTP semantics), simple mental model, wide tooling support.
- **GraphQL**: fits when clients have highly variable data needs and over/under-fetching from REST is a real, measured problem (e.g., diverse frontend clients needing different slices of the same resource graph). Costs: caching is harder, N+1 query risk moves into the schema resolvers, and it adds a new failure mode (partial success — HTTP 200 with an `errors` array).
- **gRPC**: fits internal service-to-service communication where performance (binary protocol, HTTP/2 multiplexing) and strict contract enforcement (protobuf) matter more than human-readability. Not a good fit for public/browser-facing APIs without a proxy layer.

## Versioning and backward compatibility
- Prefer **additive, backward-compatible changes** (new optional fields, new endpoints) over breaking changes wherever possible — this is the Type-1-decision discipline applied to APIs (see principles.md §8): once external consumers depend on a contract, changing it is expensive.
- If a breaking change is unavoidable, version explicitly (URL path `/v2/`, header-based, or media-type versioning) and maintain the old version for a defined deprecation window — don't silently change behavior under the same version.
- Use a schema-first or contract-first approach (OpenAPI/Pydantic models in FastAPI) so the contract is enforced by tooling, not just convention/documentation.

## Idempotency at the API layer
- `GET`, `PUT`, `DELETE` should be idempotent by HTTP semantics — repeating the call should produce the same end state. Don't build a `PUT` that behaves like `POST` (e.g., appending rather than replacing).
- `POST` for resource creation should support an idempotency key for retry safety (see distributed-systems.md) — critical for anything payment or order-adjacent.

## Pagination, filtering, and chatty APIs
- Always paginate list endpoints from day one, even if current data volume doesn't require it — retrofitting pagination onto a live API with existing clients is a breaking change (Type 1 decision) that could've been a Type 2 decision if designed in upfront.
- Prefer cursor-based pagination over offset-based for anything with high write-throughput underlying data (offset pagination skips/duplicates rows when the underlying set changes between pages).
- Watch for the **chatty API antipattern**: a client needing 10 sequential round-trips to render one screen signals a missing aggregate endpoint or a GraphQL-shaped need. This is especially costly across a service boundary (network latency compounds) — see anti-patterns.md.

## FastAPI-specific patterns
- **Pydantic models as the contract boundary**: input/output schemas should be explicit Pydantic models, not raw dicts — this gives you validation, OpenAPI docs, and a natural seam for versioning (e.g., `OrderCreateV1`, `OrderCreateV2`) for free.
- **Dependency injection (`Depends`)** is FastAPI's actual architectural tool for cross-cutting concerns (auth, DB session, current user, feature flags) — prefer it over module-level globals or manual parameter threading. It also makes testing dramatically easier (override dependencies in tests rather than mocking imports).
- **Background tasks vs Celery — don't confuse the two**: FastAPI's built-in `BackgroundTasks` runs in-process, after the response is sent, in the same worker — fine for "fire and forget, no big deal if the process restarts and loses it" work (e.g., sending a non-critical notification). For anything that must survive a process restart, needs retries, needs distributed workers, or needs to be rate-limited/throttled — that's Celery's job, not `BackgroundTasks`. Using `BackgroundTasks` for something that actually needs durability guarantees is a common and costly architectural mistake.
- **Async route handlers**: only get a benefit from `async def` if everything inside is actually async (async DB driver, async HTTP client). Mixing a blocking call (a sync DB driver, `requests` instead of `httpx`, blocking file I/O) inside an `async def` route blocks the entire event loop for all concurrent requests on that worker — often worse than just using a sync `def` route (which FastAPI runs in a threadpool). This is one of the highest-value things to check when reviewing FastAPI code.

## API error design
- Return structured, machine-parseable error bodies (error code + human message), not just an HTTP status and a string. Consumers need to branch on error *type*, not parse prose.
- Don't leak internal implementation details (stack traces, internal service names, raw DB errors) in error responses — this is both a security concern and a coupling concern (clients start depending on internal error text).
