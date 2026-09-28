---
name: systematic-debugging
description: >
  General root-cause-first debugging discipline for code bugs — distilled from obra/superpowers'
  systematic-debugging skill (MIT-licensed), adapted as a general-purpose process rather than
  copied verbatim. Distinct from k8s-debug/incident-response, which are the infra/pod-specific
  application of the same idea. Use whenever investigating a bug, test failure, or unexpected
  behavior in application code — before proposing or applying a fix.
---

# Systematic Debugging

Operationalizes the global rule "bug fix = root cause, not symptom" (CLAUDE.md §4) as an
explicit process, so the discipline survives past the first plausible-looking fix.

## The four phases

1. **Reproduce and gather evidence.** Get a reliable repro before touching code. Read the full
   error, not just the last line. Check what changed recently (`git log`/`git blame` on the
   touched area) — most bugs are a recent regression, not a latent one.
2. **Find a working comparison.** Locate a sibling case that works (another caller, another
   endpoint, the pre-regression version) and diff it against the broken one. The delta is
   usually the answer, or close to it.
3. **Form one hypothesis, test it minimally.** State what you think is wrong in one sentence
   before changing anything. Change one thing to test it. Don't stack multiple simultaneous
   changes — if it starts working, you won't know which change did it, and if it doesn't, you've
   muddied the evidence for the next hypothesis.
4. **Fix at the root, verify with evidence.** Write a failing test that reproduces the bug
   first, then fix the actual cause (not the symptom), then confirm the test passes and nothing
   else broke — see `testing-strategy` for what kind of test fits the change.

## Safeguard: three failed fixes means stop

If three attempted fixes haven't resolved it, the problem is almost certainly not what you
think it is — stop applying fixes and question the underlying assumption or architecture
instead. Continuing to guess at that point is symptom-patching by volume, not debugging.

## Warning signs you've left the process

- Proposing a fix before reproducing the bug or reading the actual error.
- Changing several things at once "to be safe."
- Calling something "probably fine" without having run the failing case again.
- Assuming the bug is simple because the symptom looks simple.

## What this skill does NOT cover

Infra/pod-level failures (`CrashLoopBackOff`, `OOMKilled`, etc.) — those have their own
evidence sources (`kubectl logs`/`describe`) and are covered by `k8s-debug` and
`incident-response`, which are this same discipline applied to that specific evidence
surface, not a different process.
