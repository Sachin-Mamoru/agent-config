# Global behavioral guidelines

Distilled from ponytail (DietrichGebert/ponytail) and karpathy-guidelines
(forrestchang/andrej-karpathy-skills), both MIT-licensed. Applies to every
coding task in every project as the base layer.

## 0. Precedence — the most specific instruction wins

1. The repo being changed: its `CLAUDE.md`/`AGENTS.md`, the docs they point to, and its
   own skills (`<repo>/.claude/skills/`). Read these before editing that repo.
2. Team-shared tooling for that repo (shared skills/commands), when present.
3. The workspace `CLAUDE.md` (multi-repo context, local-only rules).
4. These rules and the agent-config skills — the generic fallback.

When layers disagree, follow the more specific one and say which you followed. A base skill
fills gaps (how to trace a request, how to test locking); it never overrides a repo's
documented architecture, naming, testing or review conventions. Run `/ready` to load and
confirm the layers at the start of a task.

## 1. Understand before you climb

Read the task and the code it touches. Trace the real flow end to end. A
small diff you don't understand is laziness dressed up as efficiency, not
efficiency. Comprehension is never the thing being shortened.

If genuinely uncertain after reading — multiple valid interpretations, an
ambiguous requirement, a decision only the user can make — say what's
unclear and ask, or state the assumption explicitly and proceed. Don't
silently pick one interpretation and hope.

## Tooling note — library/API documentation

Before relying on training-data knowledge for a library or framework API — especially
version-specific syntax, recently-changed APIs, or anything you're not fully certain
about — check context7 (MCP) for current docs first. Training data can be stale;
context7 isn't.

Apply this with judgment: for well-established, stable APIs (stdlib, long-unchanged
library surfaces) a context7 check is unnecessary overhead — reserve it for cases
where being wrong would actually cost time (unfamiliar library, recent framework,
uncertain syntax).

## 2. The ladder — stop at the first rung that holds

1. Does this need to exist at all? (YAGNI — if speculative, skip it and say so in one line)
2. Does it already exist in this codebase? Reuse the helper/util/pattern that's already here.
3. Does the standard library do this? Use it.
4. Does a native platform feature cover it? Use it.
5. Does an already-installed dependency solve it? Use it.
6. Can this be one line? Make it one line.
7. Only then: write the minimum code that works.

Two rungs both work → take the higher (lazier) one and move on.

## 3. Surgical changes only

Touch only what the request requires. Don't drive-by refactor, reformat, or
"improve" adjacent code — match existing style even if you'd do it
differently. Every changed line should trace to the request. Clean up
orphans your own change created (now-unused imports/vars); leave
pre-existing dead code alone unless asked.

## 4. Bug fix = root cause, not symptom

A report names a symptom. Grep every caller of the function you're about to
touch and fix the shared function once — one guard there is a smaller diff
than one per caller, and patching only the reported path leaves sibling
callers still broken.

## 5. No speculative abstraction

No interface for one implementation, no factory for one product, no config
knob for a value that never changes, no "flexibility" nobody asked for.
Deletion over addition. Boring over clever — clever is what gets decoded at
3am. Fewest files possible.

## 6. Make success verifiable

Turn vague asks into checkable criteria before starting multi-step work:
"fix the bug" → write a failing repro, then make it pass. "add validation"
→ write tests for the invalid inputs, then make them pass. State the plan
as `step → verify` pairs when the task has more than one step. Weak
criteria ("make it work") invite drift; strong criteria let you loop
independently and know when you're actually done.

## 7. Mark deliberate corner-cuts

A simplification that trades correctness/robustness for size (global lock,
O(n²) scan, naive heuristic) needs a one-line comment naming the ceiling and
the upgrade path — not a silent shortcut future-you has to rediscover by
debugging it.

## 8. Never simplify away

Input validation at trust boundaries, error handling that prevents data
loss, security, accessibility, anything explicitly requested. If the user
asks for the full version after you shipped the lazy one, build it — no
re-arguing YAGNI at that point.

## 9. Output stays proportional to the ask

Code first. If asked only to build something, keep the explanation short —
what was skipped and when to reconsider it, not an essay defending the
simplification. If the user asked for a report, walkthrough, or per-phase
notes, give that in full — the terseness rule is against *unrequested*
prose, not against explanation that was actually requested.

## 10. Verify before declaring done

For non-trivial changes, actually run the repo's real checks and iterate against real
failures — don't just write code and report success from reading it.

**No completion claim without fresh evidence.** Before saying something works, passed, or is
done: name the exact command that verifies it, run it now (not a cached or earlier run), read
the full output and exit code, and confirm it actually matches the claim. "Should work,"
"probably fine," "looks correct" aren't verification — catching yourself about to write one of
those is the signal to go run the check instead of finishing the sentence.

**A passing check isn't the same as a verified invariant.** Lint/type-check/the existing test
suite only catch what they already know to look for. Brand-new code that encodes a rule —
a uniqueness constraint, an authorization check, a state-transition guard, a dedup/idempotency
check, or any second place meant to answer the same question a sibling check already answers —
can pass all three while still being subtly narrower or wider than intended, because nothing in
that loop ever restates the rule and checks the code against it. Before calling that kind of
code done: state the rule in one sentence, construct one adversarial example built to slip
through if the rule is implemented wrong, and check the actual code against it — as a real test
where practical, not just by inspection. See the `invariant-verification` skill for the full
technique and a worked example.

**Comments get the same treatment — a step, not a recollection.** Having `code-comments`
loaded doesn't stop a verbose-but-legitimate comment from shipping, because nothing forces a
check against it while writing under load. Before calling a coding task done, re-read every
comment/docstring you added in this diff as its own pass — same discipline as running the
lint/type/test commands below, not a rule to remember mid-write.

**Which checks:** the project's own — from its `CLAUDE.md`/`AGENTS.md`, README, CI config
and pre-commit hooks, in that order. Run the narrowest relevant subset first (the touched
test module), then what CI runs before calling it done. Project-specific command lists live
in that project's docs or a project skill (e.g. `python-testing` for fdm-be/udp-celery,
`web-frontend-architecture` for web), not here.

If a check needs something unavailable in this session (an interactive MFA/aws-vault prompt,
a service that isn't running, network access), say exactly which check didn't run and why —
never skip it silently.

If a check fails, fix and re-run rather than reporting the task done with a known
failure — unless the failure is pre-existing and unrelated to this change, in which
case say so explicitly rather than silently ignoring it.

## 11. Fresh-eyes review for non-trivial changes

For anything more than a small fix, suggest a second look in a fresh session (no
accumulated context from building it) before merge — a session that built something
is bad at spotting its own blind spots. This is a suggestion to surface, not something
to force.

## Working test

Fewer unnecessary changes in diffs. Fewer rewrites caused by
overcomplicating the first pass. Clarifying questions land before
implementation, not as a correction after a wrong guess.
