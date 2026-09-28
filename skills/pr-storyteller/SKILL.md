---
name: pr-storyteller
description: >
  How to write a PR description for fdm-be, udp-celery, or web — each repo has a different
  (or no) template, and existing PRs show the template is often left half-filled rather than
  actually followed. Use when asked to write, draft, or fill in a PR description, or when
  opening a PR via gh.
---

# PR Storyteller — fdm-be / udp-celery / web

## Verified state — no single convention exists (checked, not assumed)

- **fdm-be** has `.github/pull_request_template.md`: `## Related Ticket(s)` / `## Description` /
  `## Type of Change` checklist. In the last 5 merged PRs, this template was used but frequently
  left with unfilled placeholders (`<!-- Link to related tickets -->` still in the body,
  unchecked boxes) — using the template is not the same as filling it in.
- **udp-celery** has no PR template at all.
- **web** has a template, structurally different from fdm-be's — asks for a screenshot,
  Core-version compatibility, which product BEs are targeted (MedCompass/GMI Dashboard/Q&A
  checkboxes), and Core/Infra review flags. Not interchangeable with fdm-be's.
- git log style across these repos mixes Conventional Commits (`feat(scope): ...`), plain
  imperative subjects, and low-signal messages (`Update`, `Addressed comments`) — don't assume
  Conventional Commits is a hard rule, but prefer it when the recent history nearby does.

## The one PR that's actually good — use it as the model, not the template

`feat(projects) [EAE-981]: add pin/unpin for projects` — Conventional Commit type + scope,
ticket in brackets in the title, and a body that's a **tight bullet list of what actually
changed** (endpoint added, migration name, behavior notes on edge cases) with no headers, no
boilerplate, no unchecked template placeholders left in. This is the bar: a template filled in
badly is worse than a template skipped and replaced with an honest bullet summary.

## What to do per repo

### fdm-be
Use the existing template's three sections, but fill every one — never leave HTML comment
placeholders or unchecked boxes in a submitted PR:
- `Related Ticket(s)`: the actual Jira link, not the comment
- `Description`: 2-5 bullets of what changed, not a paragraph restating the title
- `Type of Change`: check the box(es) that actually apply
Title format: `type(scope) [TICKET-ID]: short description` when a ticket exists, `type(scope):
description` when it doesn't — matches the one clean example in recent history.

### udp-celery
No template to fill — write the same shape anyway (ticket link if one exists, bullet summary of
the change, note any test/coverage impact) since that's the substance the fdm-be template is
trying to get at, just without the scaffolding forcing it.

### web
Use web's own template as-is — it asks for different things than fdm-be (screenshot, Core
version, which product packages are affected, cross-team review flags) because web's actual
review process needs those, not because it's stricter or looser. Don't port fdm-be's
`Related Ticket(s)` / `Type of Change` structure into web; it doesn't match what web's
reviewers are looking for.

## What NOT to do

- Don't invent a "standard" template and propose migrating all three repos to it — the
  templates differ because the repos have different review needs (web cares about product
  targeting and screenshots; fdm-be cares about ticket traceability and change type). Matching
  reality means respecting that difference, not unifying it.
- Don't leave template placeholders in a submitted PR — an unfilled `<!-- comment -->` or
  unchecked box that should be checked is worse than not having a template, because it signals
  the form was gone through mechanically rather than actually answered.
- Don't auto-check every checkbox in web's template "to be safe" — only check what's actually
  true (e.g. don't claim Core/Infra review is needed if it isn't, don't claim coverage doesn't
  drop without having checked).
