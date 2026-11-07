---
name: code-comments
description: >
  Default to no comments in generated code; add one only for a hidden constraint, non-obvious invariant, bug workaround, or surprising behaviour, and re-read every comment and docstring in the diff before calling a task done. Use whenever writing or editing code in any repo or language.
---

# Minimal Code Comments

## The rule

Default to no comments in generated code. Add one only when it explains something the code
itself can't: a hidden constraint, a non-obvious invariant, a workaround for a specific bug, or
behavior that would genuinely surprise a reader. If a comment just restates what a well-named
function or variable already makes obvious, don't write it. Test: if removing the comment
wouldn't leave a future reader confused, it shouldn't have been there.

This applies whenever writing or editing code, in every repo and every language.

## What this looks like in practice

**Skip these:**
- Comments that describe *what* the code does when the code already reads clearly
  (`# increment counter` above `counter += 1`).
- Comments that reference the current task, ticket, or caller ("used by the X flow", "added for
  issue #123", "handles the case from PR #45") — that context belongs in the commit message or
  PR description, not the code, and it rots the moment the surrounding code changes again.
- Restating a type hint or function signature in prose.
- A comment on every step of an otherwise linear, obvious sequence.
- A comment left over from a previous version of the code that no longer matches what the code
  now does — worse than no comment, since it actively misleads.

**Keep these:**
- Why a value is what it is, when it's not derivable from the name (`RETRY_LIMIT = 3  # AWS API
  gateway hard-caps at 3 retries/sec`).
- A documented workaround for a specific upstream bug or platform quirk, ideally with a
  reference (issue link, library version).
- A note on a deliberately non-obvious tradeoff — a one-liner naming the ceiling and the
  upgrade path, not a silent shortcut (see `architecture-best-practices`'s "mark deliberate
  corner-cuts" for the fuller version of this same idea).
- An invariant that isn't visible from the immediate code ("must run before X is initialized",
  "callers guarantee this is non-empty", "NOT reversible — see module docstring").
- A short module/function-level note explaining *why* a structure exists when the shape itself
  looks arbitrary without it (e.g. why two concerns were deliberately split into separate
  columns/fields instead of one).

## Length: a comment earning its place still has to stay short

Confirmed 2026-09-21 (fdm-be): a comment can pass every test above — real, non-obvious why, not
restating the code — and still be bulkier than it needs to be. This happened repeatedly in one
session: a 6-line comment on a "kept in sync by hand across two files" invariant, a 4-line
comment on a single-word design choice (why a cast happens at one seam instead of widening a
type), a 9-line class docstring on a new enum whose four siblings each had one line. None of
these were wrong to write — they were 2-3x longer than the fact actually required.

**The tell**: if the comment would need to shrink to fit the file's existing register, it's
carrying more than the load-bearing fact. Before finishing a comment, cut it down to the one
sentence a reader actually needs, then check it against neighboring comments/docstrings in the
same file — a new class's docstring next to four one-liners should also be roughly one line,
not an essay, even if the design behind it took a whole conversation to work out. The
conversation is not the audience; the next reader of just this file is.

```python
# Too long — explains the reasoning as if narrating the decision:
# link_asset_to_project also serves system-generated linking (udp_extract,
# etc.), so it stays typed on the wider ProjectAssetType — cast the token's
# narrower file_type in at this seam rather than widening the token itself.
project_asset_type=ProjectAssetType(token.file_type.value),

# Right-sized — same fact, one line:
# link_asset_to_project also handles system-generated types, so cast here.
project_asset_type=ProjectAssetType(token.file_type.value),
```

## Docstrings

This is about inline comments, not a ban on docstrings — where a codebase already has its own
docstring convention (e.g. Google-style `Args:`/`Returns:`/`Raises:`), match it. The same
"why, not what" filter still applies inside them: don't pad a docstring with a restated
parameter description that just repeats the type hint and name back in prose.

## What NOT to do

- Don't add a comment just because a block of code "feels like it needs explaining" — if it
  needs explaining, the fix is usually a better name or a smaller function, not a comment.
- Don't leave a comment that explains a bug fix or the history of a change — that's what
  `git blame`/`git log` and the PR description are for.
- Don't over-correct into zero comments ever — a genuinely non-obvious invariant or constraint
  still deserves the one line that saves the next reader from rediscovering it by debugging.
