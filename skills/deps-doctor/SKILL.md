---
name: deps-doctor
description: >
  How to safely bump a dependency in fdm-be, udp-celery, or web by hand — none of the three
  repos has Dependabot, Renovate, or any automated dependency-update tooling, so every bump is
  manual today. Covers what to check per repo's package manager (uv vs npm), what breaks if you
  skip steps, and when proposing actual bot automation is worth raising separately.
  Use when asked to bump/upgrade a dependency, respond to a CVE, or review a dependency-bump PR.
---

# Deps Doctor — fdm-be / udp-celery / web

## Verified state — fully manual today, nothing automated

Checked directly: no `dependabot.yml`, no `renovate.json` in any of the three repos (only hit
was a vendored `renovate.json` inside `web/node_modules/comlink/`, not repo config — doesn't
count). No `.github/workflows/*.yml` in any of the three repos references dependabot or
renovate either. Every dependency bump today is a manual PR, with the exact same pre-commit
hooks (`ruff`/`mypy` for the Python repos, `oxlint`/`oxfmt`/`stylelint` via Husky for web) as
any other change — no dependency-specific CI gate exists beyond that.

## fdm-be / udp-celery (uv-managed Python)

1. Bump the version constraint in `pyproject.toml`.
2. `uv lock` — regenerates `uv.lock`. Never hand-edit the lockfile.
3. `uv sync` to pull the new version into `.venv`.
4. Run the full test suite (`aws-vault exec developer -- uv run pytest tests/`, see
   `testing-strategy` skill for direct-vs-broker mode on udp-celery) — a version bump is exactly
   the kind of change that can silently break async/Celery behavior without touching your own
   code.
5. `uv run mypy` — a minor/patch bump can still change type stubs and break the mypy gate even
   when runtime behavior is fine.
6. Check the changelog/release notes for the bumped package, not just "tests pass" — a
   silently-changed default (timeout, retry count, serialization format) can pass the existing
   test suite and still be a behavior change in production.

## web (npm)

1. Bump in `package.json`, then `npm install` (or `npm update <pkg>` for an in-range bump) to
   regenerate `package-lock.json`.
2. `npm run lint` (oxlint + stylelint) and `npm test` (Jest) — same reasoning as above, a bump
   can break lint rules or introduce a runtime break Jest catches.
3. If the bump touches `@ets/design-system` or anything in the shared `packages/components` or
   `packages/utils` surface, check usage across **all** product packages
   (fieldfocus/gmi/qa/first-draft/external), not just the one you're working in — see `web`'s
   `AGENTS.md` for the monorepo/workspace structure. A bump that's fine for QA (actively
   maintained) can silently break fieldfocus/gmi (maintenance-only, less test coverage).
4. `npm run ts-coverage` if the bump touches types — a dependency's type definitions changing is
   a common silent break in a strict-TypeScript repo.

## Security-motivated bumps (CVE response)

Treat differently from a routine bump:
- Confirm the CVE actually affects how the package is used here (a CVE in an HTTP server
  component doesn't matter if the package is only used as a client library, for instance) before
  treating it as urgent — but don't use that as an excuse to defer an actually-relevant fix.
- A CVE bump that requires a major-version jump is a case where "smallest diff" (see the global
  `AGENTS.md` ladder) is in tension with "fix the actual vulnerability" — security wins; take the
  major bump and eat the larger diff/review rather than pinning below the patched version.
- Flag CVE-motivated bumps explicitly as such in the PR description (see `pr-storyteller`) so
  reviewers know it's not optional/stylistic.

## Should this repo actually get Dependabot/Renovate?

Worth raising as a separate proposal, not bundled into this skill's day-to-day guidance:
- All three repos are candidates — none has any automated update mechanism today, so every CVE
  fix depends on someone noticing and doing the manual steps above.
- This is an infra/process change (new workflow file, possibly new required-check config), not
  something to decide unilaterally while just trying to land a single dependency bump. Mention it
  once, don't relitigate it on every bump.
