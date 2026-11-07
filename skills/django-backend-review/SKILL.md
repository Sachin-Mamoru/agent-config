---
name: django-backend-review
description: >
  Review a Django / DRF change (diff, branch, MR/PR) for correctness, security and tenant
  isolation, data integrity under concurrency, API contract compatibility, query cost on
  PostgreSQL, migrations, tests and maintainability, against the repo's own conventions; reports
  blocking findings separately from optional suggestions, each with file:line and a concrete
  failure scenario. Use when asked to review, check or approve Django/Python backend code, or
  before handing a non-trivial Django change over for review.
---

# Django backend review

## 1. Inspect

1. Get the diff (`git diff <base>...HEAD`, or the MR/PR) and the intent (issue, description). If
   you can't say in one sentence what the change is for, find out before judging it.
2. Load the repo's review bar: its `CLAUDE.md`/`CONVENTIONS`/`CONTRIBUTING` and any review
   skill or checklist the team uses. Those rules come first. This skill only adds what they
   don't cover.
3. Read the changed code **and its callers**. A changed queryset, permission or serializer
   affects every endpoint that uses it.

## 2. Check, in this order

1. **Correctness**: does it do what the intent says, including edge cases (empty, duplicate,
   None, timezone, partial update)?
2. **Security & isolation**: every queryset and related-field queryset scoped to the tenant/owner;
   `@action`/`get_permissions` overrides that dropped base permissions; user input reaching
   `extra()`/`raw()`/`RawSQL`/shell/`eval`; secrets or PII in logs and responses; unsafe file
   names and paths.
3. **Data integrity**: check-then-write races, missing constraints, slow work inside
   `atomic()`, dispatch before commit, non-idempotent tasks (`django-transactions-jobs`).
4. **API contract**: renamed or removed fields, changed status codes, error shape, default ordering,
   pagination (`django-drf-api` → api-contracts).
5. **Query cost**: N+1 in serializers/properties, `len(qs)`/`count() > 0` misuse, unbounded lists,
   new filters without indexes, `iterator()`/batching for large sets (`django-orm-performance`).
6. **Migrations**: reversible? Locks on large tables? Compatible with the previous release still
   running? Data migration isolated from model imports (`apps.get_model`)?
7. **Tests**: does a test fail without the change? Permissions matrix, adversarial case for any
   new rule, commit and race behaviour tested the right way (`django-testing`)?
8. **Maintainability**: follows the existing layering and canonical examples; no speculative
   abstraction; no unrelated changes in the diff.

For anything non-trivial, also ask the architecture questions (`architecture-best-practices` →
review-checklist) and name findings that come from that lens.

## 3. Verify findings before reporting

Confirm each suspected issue by tracing the code path, or with a quick test or query count.
Label each one: **confirmed** (traced or reproduced), **likely** (strong evidence, not run), or
**question** (needs the author's intent). Drop anything you can't support.

## Output

```
Blocking (must fix before merge)
| # | file:line | finding | failure scenario | suggested fix | confirmed/likely |

Should fix (real risk, may be a follow-up)
| … |

Optional (style, naming, small improvements — mention once)
- …

Verified fine: <things checked that look right, briefly — so the author knows they were covered>
Checks run: <commands + results>; not run: <what and why>
```

Write comments as you'd say them to the author: what you checked, the concrete failure, the fix.
No filler praise, no vague "consider refactoring".

## Example prompts

- "Review my branch against main — focus on tenant isolation and query counts."
- "Review this MR that adds bulk delete for workspaces; is it safe under concurrent requests?"
- "Before I open the MR: review the migration in this diff for locking on a large table."

## Sources

- Django security topics: https://docs.djangoproject.com/en/stable/topics/security/
- Django deployment checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
- DRF permissions: https://www.django-rest-framework.org/api-guide/permissions/
- Writing migrations (non-atomic, reversibility, `apps.get_model`): https://docs.djangoproject.com/en/stable/howto/writing-migrations/
