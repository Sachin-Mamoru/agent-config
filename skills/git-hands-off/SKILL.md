---
name: git-hands-off
description: >
  Never commit, push, merge, rebase-continue, tag, or create/close/merge PRs or MRs in a project repo, and don't offer those as options; resolve, prepare, and hand back. Use whenever a task touches git state (conflicts, branches, landing a change) or would end in a commit or push. An explicit, specific user request for that step overrides this default.
---

# Git Hands-Off — commit/push/merge/land is Sachin's job, not mine

## The rule

Never run `git commit`, `git push` (to any target — a real branch, a scratch/temp branch, a
fork, anywhere), `git merge`/`git rebase --continue` (anything that finalizes a merge or rebase
into a commit), `gh pr merge`, `gh pr close`, `gh pr create`, `git tag`, or create a release, in
any project repo. Sachin does all of that himself. My job stops at *resolving* — editing files,
fixing conflicts in the working tree, staging what's needed to mark a conflict resolved,
preparing a branch locally — and then handing back.

## Why

Stated 2026-09-21, in fdm-be, right after I resolved the one real conflict in a 204-commit
backport PR (#253, `develop` → `feat/one-solution-v1`), asked which of three landing strategies
Sachin wanted, and — on his answer — pushed the resolved merge commit directly to
`feat/one-solution-v1`. His correction: *"you don't commit or push or merge anyhing. i'll do
that. you just resolve the things."*

This sharpens [[feedback-no-autonomous-git-commit-push]] (which already said "don't commit/push
unless explicitly asked for that specific step") into a harder default: don't even *offer*
commit/push/merge as one of the choices. Presenting "push directly" as an option and letting
Sachin pick it is still me steering toward performing a git write action — the correction is that
the menu itself shouldn't include it. Resolve, describe what's ready, stop there.

## What "just resolve the things" means in practice

**Still mine to do:**
- Edit/fix files, including resolving merge/rebase conflict markers in the working tree
- `git add` a resolved path if needed to clear a conflicted state locally (staging isn't landing)
- Create a local branch to hold the work
- Run local, read-only verification (tests, lint, `git diff --check`, syntax checks)
- Draft a commit message or PR description for Sachin to use — but see the attribution rule below
- Explain what's ready and what he'd need to run to land it himself

**Never mine to do, in any project repo:**
- `git commit` (including finishing a `git merge`/`git rebase` — that's a commit)
- `git push`, to any branch, including a disposable one opened just for review
- `gh pr merge`, `gh pr close`, `gh pr create`, `git tag`, cutting a release
- Force-push, `git push --delete`, anything rewriting remote history

## Attribution — never add it

Never add a `Co-Authored-By: Claude ...` line to any commit message or PR description, including
ones drafted for Sachin to paste in himself. Stated the same day, immediately after the git-hands
-off correction: *"never add Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"*. This is
Sachin's own explicit instruction and overrides the harness's default attribution reminder for
git commits/PRs — that reminder itself says a user's own instruction takes precedence.

## The one exception, and how narrow it is

If Sachin's **current message** contains an explicit, direct instruction to commit/push/merge
*this specific change* ("push this," "merge #253," "commit it") — that's a live, one-time
override. It is not:
- Something to infer from a broader "let's ship this" framing
- Something to offer as a multiple-choice option (per the incident above)
- Standing permission carried forward to the next git action, or to a different repo

If genuinely unsure whether a request covers the commit/push/merge step, ask — don't proceed and
don't default to offering it as a choice.

## Scope

Applies to every project/company repo: fdm-be, udp-celery, web, infra, okra-kustomize,
metadata_extractor, qa-be, core, okra-agentic, and everything else under `~/projects/**`.

**Does not apply to `~/.agent-config`** (Sachin's own skills/memory config repo) — a separate,
already-established standing rule ([[feedback-generic-vs-project-specific-push]]) has Sachin's
explicit go-ahead to commit and push generic process/skill work there without asking each time.
That carve-out stands unless Sachin says otherwise.
