---
name: secret-guard
description: >
  How to add and reason about secret scanning across fdm-be, udp-celery, and web — none of them
  have a dedicated secret scanner today, only a narrow detect-private-key hook in the two Python
  repos. Covers tool choice, wiring into each repo's actual hook mechanism, what to scan for given
  this stack, and what to do if a secret is actually found (no documented precedent exists yet).
  Use when asked to add secret scanning, review a diff for leaked credentials, or respond to a
  suspected committed secret.
---

# Secret Guard — fdm-be / udp-celery / web

## Current state (verified, not assumed)

- No `gitleaks` or `detect-secrets` binary installed anywhere, no `.gitleaks.toml` or
  `.secrets.baseline` config in any repo. This is greenfield — no existing tool to migrate off of.
- fdm-be and udp-celery each carry `detect-private-key` (from the stock `pre-commit-hooks` repo)
  in their `.pre-commit-config.yaml` — catches PEM/SSH private key blocks only, nothing else
  (no AWS keys, no JWTs, no API tokens, no DB connection strings).
- web has **no** Python `pre-commit` at all, but it does have a working git-hook mechanism:
  `.husky/pre-commit` and `.husky/pre-push` both run `npx lint-staged`, which currently only does
  oxlint/oxfmt/stylelint — no secret scanning.
- No documented leaked-secret incident or rotation runbook exists anywhere in the promoted or
  original Copilot skills (checked `incident-response`, `env-mapping`, and all 15 skills broadly).
  Don't assume there's an established response pattern — the "what to do if found" section below
  is designed from scratch, not distilled from a past incident.

## Tool choice: gitleaks

Prefer **gitleaks** over `detect-secrets` for this stack:
- Single static binary, no Python dependency — works identically in the two `uv`-managed Python
  repos and the npm-managed web repo without adding a second language's tooling to either
- Runs fine as a `local` hook in Python `pre-commit` (fdm-be/udp-celery) and as a plain CLI call
  from `lint-staged`/Husky (web) — same config format (`.gitleaks.toml`) in both cases
- Scans the diff being committed, not the whole repo, by default (`gitleaks protect
  --staged`) — fast enough for a pre-commit hook

## Wiring into each repo — use the mechanism that's already there, don't introduce a new one

### fdm-be / udp-celery (Python `pre-commit`)
Add as a `local` hook alongside the existing `ruff`/`mypy` entries in `.pre-commit-config.yaml`:
```yaml
  - repo: local
    hooks:
      - id: gitleaks
        name: gitleaks secret scan
        entry: gitleaks protect --staged --redact -v
        language: system
        pass_filenames: false
```
Keep `detect-private-key` — it's redundant with gitleaks' own key detection but costs nothing to
leave in place, and removing an existing hook is a separate decision from adding a new one.

### web (Husky + lint-staged)
Don't route this through `lint-staged`'s per-file globs (gitleaks needs the staged diff as a
whole, not a file list). Add a second line to `.husky/pre-commit` before the `lint-staged` call:
```
gitleaks protect --staged --redact -v
npx lint-staged
```
This keeps the existing lint/format flow untouched and fails fast on a secret before spending time
on linting.

## What actually matters to scan for, given this stack

Generic gitleaks rules cover AWS access keys and most vendor API key formats out of the box. Add a
custom rule set (or `.gitleaks.toml` allowlist tuning) for what's specific here:
- **Cognito tokens** (`SESSION_TOKEN`, `SESSION_REFRESH_TOKEN`) — these show up in ad-hoc scripts
  and perf-test env vars (see `fdm-perf-test` skill's env var list) and are easy to paste into a
  throwaway script and forget
- **JWT upload tokens** — the confirm-upload flow (see `project_confirm_upload` memory) mints
  short-lived JWTs; a hardcoded one in a test fixture is a plausible false-negative for generic
  rules since it doesn't look like a vendor key format
- **DB passwords** — local dev already uses a known throwaway password (`postgres`/`postgres` on
  `localhost:5433`), so tune the allowlist to not flag that specific local pattern and avoid
  training the team to ignore every DB-password hit as a false positive
- **LLM provider API keys** (OpenAI, Anthropic, etc.) — metadata_extractor and the eval notebooks
  make live calls; a key pasted into a notebook cell for a quick test is a realistic leak vector
- **AWS Secrets Manager ARNs are not secrets themselves** — don't let a scanner flag
  `SYSTEM_TOKEN_IAM_ARN`-style references as findings; only the actual resolved secret value
  matters

## If a secret is actually found in a diff or in history

There's no established runbook for this — treat it as a real incident, not a lint failure:

1. **Don't just delete the line and recommit** — if it was ever pushed, it's in git history and
   recoverable regardless of the current file state. Rewriting history (`git filter-repo` /
   force-push) is a separate, higher-risk decision — flag it to Sachin rather than doing it
   autonomously (per standing guidance: no autonomous git commit/push, and this is well beyond
   that bar).
2. **Rotate the credential first, before cleaning up history.** A secret that's already been
   pushed should be treated as compromised the moment it's confirmed, independent of whether
   anyone is known to have seen it.
3. **Identify blast radius**: which environment does the credential belong to (development /
   staging / acceptance / production — see `env-mapping` skill for the account/namespace map)?
   Production credentials get escalated faster than a development-only key.
4. Only after rotation is confirmed, decide whether history rewrite is warranted (small young
   branch vs. long-merged `develop` history changes the calculus significantly).

## What this skill does NOT cover

CI-level scanning (e.g. a GitHub Actions step that re-scans on push as a backstop to the local
hook) — none of the three repos' workflows currently do this (see the workflow inventory: none of
fdm-be/udp-celery/web's `.github/workflows/*.yml` reference gitleaks or detect-secrets). Adding
that is a reasonable follow-up but is a CI change, not a local pre-commit change, and should be
proposed separately.
