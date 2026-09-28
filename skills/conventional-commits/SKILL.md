---
name: conventional-commits
description: >
  How to write commit messages for fdm-be, udp-celery, and web — each repo has a genuinely
  different convention today (checked git log directly, not assumed), so this is a per-repo
  guide, not one format applied everywhere. Use when asked to commit changes, write or fix a
  commit message, or decide whether/how to reference a Jira ticket in a commit.
---

# Conventional Commits — per repo, not universal

## Verified state — three different conventions, no shared standard

- **fdm-be**: mixed. Some commits follow Conventional Commits (`feat(projects): ...`,
  `refactor: ...`), many don't (`Update`, `Addressed comments`, `minor updates`). Ticket keys
  occasionally appear in the subject — bracketed (`feat(projects) [EAE-981]: add pin/unpin for
  projects`) or parenthesized (`... (EAE-946)`) — but most commits carry no ticket reference at
  all. `pr-storyteller`'s "one clean example" is this repo's bracketed-subject style.
- **udp-celery**: fairly consistent `type: description` (`feat:`, `fix:`, `refactor:`,
  `chore:`, `tests:`, `configs:`) — no scope parens in most commits, no ticket keys in the
  commit subject at all. Tickets surface only in branch/PR names (e.g. `FDM-V3`), never in
  individual commit messages.
- **web**: no type-prefix convention whatsoever — commits are full descriptive sentences
  (`Refactor PdfPreview component to utilize useMemo for URL construction...`). Ticket keys
  (`EAE-755`, `EAE-869`) appear only on merge-commit/PR titles, never on the commits that make
  up the PR.
- **No confirmed Jira-GitHub smart-commit integration anywhere** — didn't find evidence any
  commit-message trailer is actually parsed by Jira in these repos. Don't invent a `Refs:`-style
  footer convention on the assumption it links anything; if a ticket needs to be referenced,
  match whatever the repo's own history actually does (see above), not a generic trailer spec.

## What to do, per repo

- **fdm-be**: default to Conventional Commits (`type(scope): description`) since roughly half
  of recent history already does. Add the ticket key in the subject, bracketed, only when the
  PR itself doesn't already carry it in the title (per `pr-storyteller`'s title format) —
  don't double up.
- **udp-celery**: match `type: description`, lowercase, no scope unless the repo's own recent
  commits use one. Don't add a ticket key to the commit message — this repo's convention puts
  that on the branch/PR, not the commit.
- **web**: don't impose a type-prefix format unilaterally — write a plain, specific descriptive
  sentence matching the dominant style, unless the user explicitly asks to start using
  Conventional Commits here.

## Mechanics (when Conventional Commits format applies — fdm-be, udp-celery)

- Header: `type(scope): description`, lowercase type, imperative mood, no trailing period.
- `feat` = new capability, `fix` = bug fix, `refactor`/`chore`/`test`/`docs`/`ci`/`build` for
  the rest. Breaking change → `type(scope)!: ...` plus a `BREAKING CHANGE:` footer paragraph.
- One logical change per commit — a feature and an unrelated fix in the same diff is two
  commits, not one with a longer message.
- Don't `git add -A` to force everything into one commit — stage only what belongs together;
  ask if it's unclear what should be split.

## What this skill does NOT cover

Whether Jira actually has a GitHub integration that reads commit trailers for this org —
unconfirmed. If a user asks for "proper Jira linking" in a commit, ask what mechanism is
actually wired up rather than assuming a trailer format works.
