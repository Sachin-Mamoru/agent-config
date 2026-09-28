---
name: architecture-best-practices
description: Software architecture and system design best practices, distilled from renowned architects (Fowler, Kleppmann, Cockcroft, Newman, Nygard, Evans, Kim, Vernon, and others). Use whenever reviewing a design or PR, designing a new system/service, improving or refactoring an existing system, evaluating a technical proposal, debating a tech choice, writing an ADR, diagnosing reliability problems, or reasoning about microservices vs monolith, sync vs async, coupling/cohesion, API design, distributed systems consistency, or infra/deployment architecture (Kubernetes, AWS, EKS, Celery, autoscaling). Trigger for questions like "should this be a separate service," "how should I structure this," "is this a good design," "what's wrong with this system," or "how do I scale this" — not just explicit "review my architecture" requests.
---

# Software Architecture & Engineering Best Practices

A working reference for architecting, reviewing, and improving systems — grounded in the reasoning of the field's most respected practitioners, not just rules of thumb.

## How to use this skill

1. **Identify the mode**: reviewing existing code/design, designing something new, improving/refactoring a live system, or making a specific technology decision. The approach differs for each (see below).
2. **Load the relevant reference file(s)** — don't try to hold everything in working memory. This SKILL.md is the map; the references are the territory.
3. **Reason from principles, not vibes**. Every recommendation should trace back to a named principle or trade-off, not "best practice" as an unexamined slogan. State the trade-off, not just the recommendation.
4. **Always surface the cost side.** Every architectural choice trades something for something else. A recommendation without a stated cost is incomplete and should be treated as a red flag in your own reasoning.

## Reference files (read what's relevant, not everything)

- `references/principles.md` — Core distilled principles from named architects (Fowler, Kleppmann, Cockcroft, Newman, Nygard, Evans, Vernon, Kim, Beck, Ousterhout, Hickey and others), organized by theme. This is the philosophical backbone — read this first for any non-trivial design question.
- `references/review-checklist.md` — Structured checklist for reviewing designs, PRs, or existing systems. Use when the ask is "review this" or "what's wrong with this."
- `references/system-design-process.md` — Step-by-step process for greenfield design: requirements → constraints → trade-off analysis → ADR. Use when the ask is "design a system for X" or "should I build this as a separate service."
- `references/distributed-systems.md` — Consistency models, CAP/PACELC, idempotency, event-driven patterns, saga pattern, outbox pattern, distributed transactions — Kleppmann/Newman territory.
- `references/api-design.md` — REST/GraphQL/gRPC design, versioning, backward compatibility, FastAPI-specific patterns (Pydantic schemas, dependency injection, background tasks vs Celery).
- `references/python-fastapi.md` — Python and FastAPI-specific architecture patterns: layering, dependency injection, async pitfalls, Celery/RabbitMQ task architecture, testing strategy.
- `references/aws-k8s-infra.md` — AWS and Kubernetes/EKS deep dive: cluster architecture, autoscaling (HPA/KEDA/Cluster Autoscaler), networking, IAM, cost optimization, observability (Dynatrace/Logfire-style), CI/CD.
- `references/react-frontend.md` — React/frontend architecture: component design, state management, data fetching patterns, performance.
- `references/anti-patterns.md` — Named anti-patterns and smells (distributed monolith, big ball of mud, god object, chatty API, N+1, premature microservices) with the "why" behind each.
- `references/adr-template.md` — Architecture Decision Record template + worked example.

## The one meta-principle that overrides all others

**Reversibility beats optimality.** Fowler's "Yagni" and Bezos's "Type 1 vs Type 2 decisions" both point the same direction: an 80%-good decision you can reverse cheaply beats a 95%-good decision that locks you in. When advising, always ask: how expensive is it to change this later? That question should shape the recommendation more than which option is theoretically "best" in isolation.

## Quick-reference: the questions a good architect always asks

Before recommending any design, run the request through these (expanded with sources in `references/principles.md`):

1. **What problem is this actually solving, and for whom?** (Evans — start from the domain, not the tech)
2. **What's the blast radius if this fails?** (Nygard — design for failure, not just success)
3. **Who needs to change this code in 6 months, and how easily can they?** (Fowler — coupling/cohesion is a people problem as much as a technical one)
4. **What's the simplest thing that could possibly work?** (Kent Beck / XP tradition — complexity must be earned, not assumed)
5. **What are we optimizing for — and what are we explicitly willing to sacrifice?** (Kleppmann — every distributed systems choice is a trade-off across consistency, availability, latency)
6. **Is this decision reversible?** (see meta-principle above)
7. **Does the team's structure match the architecture we're proposing?** (Conway's Law — often the real reason a "clean" microservices design fails in practice)

## Calibrating to context (Sachin's stack)

When the conversation involves the person's actual work context, bias toward these specifics rather than generic advice:
- Backend: Python, FastAPI, Pydantic, async SQLAlchemy patterns
- Task processing: Celery + RabbitMQ, KEDA-based autoscaling
- Infra: AWS, EKS/Kubernetes, observability via Dynatrace/Logfire
- Frontend: React
- Org context: Associate Technical Lead reviewing others' PRs/designs as often as writing greenfield code — so the review-checklist and anti-patterns references are frequently the most relevant entry points, not just system-design-process.

Don't force this context into unrelated questions (e.g. a pure algorithms question, or a different client's stack) — apply it when the query is actually about their systems or when they ask for a review/design in that stack.
