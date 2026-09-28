---
name: invariant-verification
description: >
  General discipline for any code that encodes a rule/invariant (uniqueness, authorization,
  state transitions, dedup, idempotency) rather than plain plumbing: state the rule in one
  sentence, then check the actual code against an adversarial example built specifically to
  slip through if the implementation is subtly narrower or wider than the rule. Use before
  calling any such code done — ordinary lint/type-check/existing-tests can't catch this class
  of bug, because nothing in that loop ever restates the rule. See `db-constraint-design` for
  the Postgres-specific instance this was generalized from.
---

# Invariant Verification — check the rule, not just the code

## Why this exists

Built after two real bugs in the same fdm-be feature, same shape, different code:

1. A Postgres unique index (`uq_project_assets_file_name`) put a scoping column
   (`file_type`) only in `postgresql_where`, not in the key — so two different-typed files
   sharing a name would have incorrectly collided. Full writeup: `db-constraint-design`.
2. `missing_required_file_types` (the signal a frontend uses to enable/disable a Generate
   button) counted a required file as "present" the moment it existed, without checking
   whether its UDP processing had actually finished — while the real generation gate
   (`validate_generation_sources`) *did* check that. Same project, same session, same root
   cause: a condition that mattered was enforced in one place and silently absent from the
   sibling place that was supposed to answer the same question.

Both passed `ruff`, `mypy`, and the full existing test suite. Both were real, live bugs.

## The general failure pattern

Ordinary verification — lint, type-check, run the existing tests — only catches what it
already knows to check for. Brand-new code that encodes a rule can pass all three while still
being wrong, because nothing in that loop ever restates the rule and checks the code against
it. This is a translation gap between "the rule in my head" and "the code I wrote," not a
knowledge gap — the syntax is usually fine; the *scope* of what got encoded is off by one
condition. It's especially invisible when the code that's missing the condition still "looks
right" in isolation and only breaks when compared against a sibling that got it right.

## Which code this applies to

Apply it to anything translating "the rule is X" into a boolean expression, a filter, a query,
or a set of allowed values:
- Uniqueness/dedup logic — DB constraints (`db-constraint-design`), but also in-memory dedup,
  idempotency keys, cache keys
- Authorization/ownership checks — "who is allowed to do X"
- State-machine/readiness checks — "what statuses count as done," "what transitions are legal"
  (the `missing_required_file_types` bug above is this category: "present" vs "ready")
- Validation logic with more than one condition ANDed/ORed together
- Any pair of code paths meant to answer the *same* underlying question from two places (a
  soft gate for a UI signal, a hard gate enforced server-side) — these are exactly where one
  side silently drifts narrower or wider than the other, because nothing forces them to share
  the check.

Don't apply this heavyweight process to plumbing: a router forwarding to a service, a schema
field rename, a straightforward CRUD passthrough. That's what CLAUDE.md's ladder and "surgical
changes only" already guard against turning into unneeded process — reserve this for code that
actually decides something.

## The technique

1. **State the rule in one plain sentence**, using domain terms, not variable names — "a
   required file type is satisfied when at least one upload of that type exists *and has
   finished UDP processing*," not "present_types minus required."
2. **Construct one example that must pass and one adversarial example** built specifically to
   slip through if the code is narrower or wider than the sentence in step 1. If there's a
   sibling piece of code answering a related question, use it as the adversarial source: "what
   does the sibling check that this one doesn't?"
3. **Check the actual code against both** — trace it by hand, or better, write it as a real
   test. If a sibling/hard-gate version of the same check exists elsewhere, read it side by
   side with the one you just wrote before considering either one done.
4. If no existing test in the suite exercises the adversarial example, that's the gap itself —
   "everything passes" is only evidence for what the suite already thought to check, not for
   the rule you just wrote.

## Why existing checks don't catch this

`ruff`/`mypy` verify shape and types, not intent — a WHERE-only scoping column and an
existence-only readiness check are both perfectly well-typed. The test suite only catches
regressions in behavior it already has an assertion for; brand-new rule-encoding logic has no
such assertion yet by definition. "68 failed, 572 passed, same as before" is real evidence that
a change didn't break anything *already tested* — it says nothing about whether the new rule
itself is right.

## What NOT to do

- Don't run this process on plumbing code — it's for genuine rule/invariant logic, not every
  line written.
- Don't treat "tests pass" as proof a brand-new rule is correct — passing tests only prove the
  code matches what the *existing* suite already expected.
- Don't stop at "traced it by hand and it looked right" for logic that will run repeatedly or
  that other people will touch later — write the adversarial example as a real test where
  practical. The app-level pre-check in `db-constraint-design`'s incident made the identical
  mistake as the DB constraint it was supposed to mirror, independently, because nobody wrote
  the coexistence case as a test.
- Don't assume a sibling check with a stricter condition is automatically the "buggy" one that
  needs relaxing, or the looser one is automatically fine — read both, decide which one
  actually reflects the intended rule, then make the other match it.

## See also

`db-constraint-design` — this technique applied specifically to Postgres unique
constraints/indexes, the incident this skill was generalized from.
