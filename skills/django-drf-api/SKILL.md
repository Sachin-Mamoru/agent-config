---
name: django-drf-api
description: >
  Implement or change Django / Django REST Framework endpoints in an existing codebase. Traces
  URL → middleware → authentication → permissions → view/viewset → serializer → ORM, picks the
  right hook (get_queryset, get_serializer_class, perform_create/perform_update, @action),
  enforces ownership/tenant scoping and object permissions, and keeps the API contract (status
  codes, errors, filtering, ordering, pagination, versioning, uploads, async job resources,
  idempotency) backward compatible. Use when adding or modifying an endpoint, serializer,
  permission class, router registration or custom action; when an API returns an unexpected
  401/403/404/400; or when designing request/response shapes, pagination or versioning.
---

# Django / DRF endpoint work

The repo's own docs (its `CLAUDE.md`, conventions, contributing guide, a canonical example
endpoint) win over everything here. This skill is the fallback procedure and the set of DRF
behaviours that are easy to get wrong.

## 1. Inspect (before writing code)

1. **Versions** — read the dependency manifest and lockfile (`pyproject.toml`, `uv.lock`,
   `poetry.lock`, `requirements*.txt`) for `django`, `djangorestframework`, `django-filter`,
   `drf-spectacular`/`drf-yasg`, `psycopg`. Don't give version-specific advice before this.
2. **Global API config** — `REST_FRAMEWORK` in settings: `DEFAULT_AUTHENTICATION_CLASSES`,
   `DEFAULT_PERMISSION_CLASSES`, `DEFAULT_PAGINATION_CLASS`, `DEFAULT_FILTER_BACKENDS`,
   `DEFAULT_VERSIONING_CLASS`, `EXCEPTION_HANDLER`. Then `MIDDLEWARE`: note any middleware
   that attaches tenant/organization/context to `request`.
3. **Closest sibling** — find the existing endpoint most like the task (same resource family,
   same base classes). Copy its shape: base viewset/mixins, permission classes, serializer
   split, service calls, schema decorators, and its tests.
4. **Trace the real request path** for the endpoint you'll touch and write it down in one line:
   `urls.py route → view.action → auth classes → permission classes (class + action) →
   get_queryset → serializer → service/model → response`. Details:
   [references/request-flow.md](references/request-flow.md).

## 2. Implement — put each concern where DRF expects it

| Concern | Where it goes |
|---|---|
| Which rows this user may see or touch | `get_queryset()` scoped by owner/tenant. List endpoints never call object permissions, so the queryset is the list's only guard. |
| May this actor do this action on this object | `permission_classes` + `has_object_permission()`; it only runs via `get_object()` / `check_object_permissions()`. |
| Different input/output shape per action | `get_serializer_class()` (e.g. create vs. response vs. list serializers). |
| Server-owned fields (owner, tenant, created_by) | Read-only on the serializer; set in `perform_create(serializer.save(owner=...))`, or `HiddenField(default=CurrentUserDefault())` when a validator needs the value. |
| Input shape and cross-field rules | `validate_<field>()` / `validate()`; use the project's choice field if it wraps `ChoiceField`. |
| References to other rows in the body | Related fields with a **scoped** queryset (only the caller's tenant), never `Model.objects.all()`. |
| Business rules, state transitions, side effects | Where the project already puts them (service module, model method). Add a service function only if there's a second caller or real logic to name. |
| Non-CRUD operation on a resource | `@action(detail=True, methods=["post"])`; mind the permission rule below. |
| Concurrent state changes | See `django-transactions-jobs`. |

Rules that cause real bugs:

- **`@action(permission_classes=[...])` replaces** the viewset's list — it doesn't add to it.
  Same for overriding `get_permissions()`. Re-include the base permissions you still need.
- **401 vs 403**: an unauthenticated request that fails a permission check gets 401 only if the
  first authentication class returns a `WWW-Authenticate` header (token/basic style); with
  session-style auth first it gets 403. Check the order before writing tests that assert 401.
- **404 instead of 403 is often intentional**: scoping `get_queryset()` makes objects in other
  tenants 404, which doesn't reveal that they exist. Match what sibling endpoints do.
- **Read-only fields are ignored on input, not rejected** — a client sending `owner` gets 200 and
  nothing changes. Test that it really didn't change.
- **Explicit `fields`** on input serializers, never `"__all__"` (mass assignment).
- **PATCH** goes through `partial=True`; `validate()` then sees only the submitted fields — read the
  rest from `self.instance`. `HiddenField` values are absent under `partial=True`.
- A `read_only=True` field doesn't use its `default`, so a `UniqueTogetherValidator` that
  includes it breaks. Use `HiddenField(default=CurrentUserDefault())` for server-set parts of a
  unique key.

## 3. Keep the API contract

Before changing a response, filter, ordering or pagination, read
[references/api-contracts.md](references/api-contracts.md): error shape, status codes,
allowlisted filtering/ordering, choosing a pagination style, stable ordering, versioning
without breaking clients, uploads, async job resources, and idempotency keys.
Adding a field is usually safe. Renaming or removing one, changing a type, tightening
validation, or changing a default ordering or page size breaks existing clients.

## 4. Verify

- Tests per `django-testing`: a permission matrix (anonymous, other tenant, owner, admin),
  validation failures, the happy path, a read-only-field-ignored case, and a query-count guard
  for list endpoints.
- For any new authorization or state rule, run `invariant-verification`: state the rule in one
  sentence and add one adversarial test, for example another tenant's id in the URL or body.
- Regenerate or validate the OpenAPI schema if the project publishes one.
- Run the repo's lint and test commands for the touched modules, then what CI runs.

## Output

1. **Trace**: the one-line request path, plus anything surprising (middleware, auth order).
2. **Changes**: each file touched and why, in one line each.
3. **Verification**: the exact commands run and their results, and which checks couldn't run.
4. **Contract impact**: "none", or what clients will see.
5. **Out of scope**: production improvements noticed, listed separately and not implemented.

## Example prompts

- "Add `POST /orders/{id}/cancel/` — only the owner may cancel, only from `pending`/`paid`, and two
  simultaneous cancels must not both succeed."
- "Why does `GET /projects/12/` return 404 for an org admin but 200 for the owner?"
- "Add `status` filtering and `-created_at,id` ordering to the invoices list without changing the
  existing response."
- "This viewset's `export` action is reachable by read-only users — find out why and fix it."

## Sources

- DRF request lifecycle, generic views and viewsets: https://www.django-rest-framework.org/api-guide/generic-views/ ,
  https://www.django-rest-framework.org/api-guide/viewsets/#marking-extra-actions-for-routing
- Permissions, object permissions, 401 vs 403: https://www.django-rest-framework.org/api-guide/permissions/ ,
  https://www.django-rest-framework.org/api-guide/authentication/#unauthorized-and-forbidden-responses
- Serializers, validators, `CurrentUserDefault`/`HiddenField`: https://www.django-rest-framework.org/api-guide/serializers/ ,
  https://www.django-rest-framework.org/api-guide/validators/ , https://www.django-rest-framework.org/api-guide/fields/#hiddenfield
