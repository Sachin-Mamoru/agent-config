# API contracts: shape, errors, filtering, pagination, versioning, uploads, jobs, idempotency

Follow the project's existing conventions first. Grep two or three sibling endpoints and copy
their choices. Use this file for decisions the project hasn't made yet.

## Compatibility rules

Safe: adding an optional request field, adding a response field, adding an endpoint, adding an
enum value **if** clients tolerate unknown values.

Breaking: removing or renaming a field, changing a type or nullability, making an optional
input required, tightening validation on existing input, changing status codes, error shape,
default ordering, default page size or pagination style, changing an id format.

For a breaking change: add the new behaviour alongside the old one (new field, new endpoint,
new version), mark the old one deprecated in the schema and changelog, and remove it only after
clients have moved.

## Status codes and errors

| Case | Code |
|---|---|
| Created a resource | 201 (+ body of the resource) |
| Accepted async work | 202 + a job resource (see below) |
| Deleted, nothing to return | 204 |
| Input invalid (shape, field rules) | 400 with field → messages, DRF's default `ValidationError` shape unless the project customises it |
| Not authenticated / denied | 401 / 403 — see request-flow.md |
| Not found or intentionally hidden | 404 |
| Valid input but conflicts with current state (already cancelled, version mismatch, duplicate) | 409 |
| Rate limited | 429 |

Keep one error shape across the API. If the project has a custom `EXCEPTION_HANDLER` or error
version header, raise the project's exceptions and don't build ad-hoc `Response({"error": ...})`.

## Filtering and ordering — allowlist only

- Filtering: declare the filterable fields (`django-filter` `filterset_fields`/`FilterSet`, or
  explicit query-param parsing through a serializer). Never pass raw query params into
  `filter(**request.query_params)`.
- Ordering: set `ordering_fields` explicitly. Without it, DRF's `OrderingFilter` allows any
  readable serializer field, and `"__all__"` exposes every model field. Multi-field ordering
  (`?ordering=-created_at,id`) is supported once the fields are allowlisted.
- Always end the ordering with a unique tie-breaker (`id`/`pk`). Otherwise rows with equal sort
  keys can repeat or vanish between pages.
- Validate filter values (types, enums) like any other input; invalid ones → 400, not 500.
- Each new filter or ordering field is a query shape: check it has an index if the table is
  large (see `django-orm-performance`).

## Pagination — choose by access pattern

| Style | Use when | Costs |
|---|---|---|
| `PageNumberPagination` | UI with page numbers, small/medium tables | `COUNT(*)` per request; deep pages scan and skip rows |
| `LimitOffsetPagination` | Clients need arbitrary offsets | Same `COUNT(*)` and deep-offset cost; rows shift if data changes between requests |
| `CursorPagination` | Large or fast-growing tables, infinite scroll, sync/export | Needs an ordering on an unchanging, (nearly) unique field; no jump to page N, no total count; the ordering is fixed by the view |

Rules: paginate every list that grows with usage; keep the existing style on existing endpoints
(switching is a breaking change); add a `max_limit`/`max_page_size`.

## Versioning

- Find the project's scheme first (`DEFAULT_VERSIONING_CLASS`, URL prefixes, an error-version
  header, or "no versioning — additive changes only").
- DRF options: `URLPathVersioning`, `NamespaceVersioning`, `AcceptHeaderVersioning`,
  `HostNameVersioning`, `QueryParameterVersioning`; branch on `request.version` in
  `get_serializer_class()` rather than duplicating views.
- Prefer additive evolution plus deprecation over a new version. Introduce a version only
  for a change that can't be additive.

## File uploads

- Use `MultiPartParser`/`FileUploadParser` as the project does. Validate size, extension *and*
  content type, and don't trust the client-sent filename (normalise it, or generate a storage key).
- Size limits: Django's `DATA_UPLOAD_MAX_MEMORY_SIZE` and `FILE_UPLOAD_MAX_MEMORY_SIZE` cover
  memory and disk spooling only. Add an explicit max-size check, and have the proxy enforce a body limit.
- For large files, prefer direct-to-storage uploads (pre-signed URL), then a confirm call
  that the API validates.
- Authorise downloads the same way as the owning resource. Serve via short-lived signed URLs
  rather than public ones.

## Long-running work as a job resource

`POST /exports/` → 202 + `{"id": ..., "status": "pending"}` and a `Location` header for
`GET /exports/{id}/` (status, progress, result URL or error). Create the job row and enqueue
the work after commit (see `django-transactions-jobs`). Cancellation is a state change on the
job (`POST /exports/{id}/cancel/`) that the worker must check cooperatively.

## Idempotency for retried requests

Use it for creates and side-effecting actions that clients or proxies may retry (payments,
orders, external calls):

- Client sends `Idempotency-Key`. Store `(tenant, key)` with a unique constraint, a hash of
  the request, and the response.
- On a repeat with the same key: return the stored response. If the request body differs,
  return 409/422.
- Insert the key row in the same transaction as the work, and rely on the unique
  constraint, not on a "check then insert" (that races).
- Natural idempotency is often simpler: a unique constraint on the business key plus
  `get_or_create`, or a state-transition update that only succeeds once
  (`filter(status="pending").update(status="cancelled")`).

Sources: https://www.django-rest-framework.org/api-guide/pagination/ ,
https://www.django-rest-framework.org/api-guide/filtering/#orderingfilter ,
https://www.django-rest-framework.org/api-guide/versioning/ ,
https://www.django-rest-framework.org/api-guide/exceptions/ ,
https://www.django-rest-framework.org/api-guide/parsers/#fileuploadparser ,
https://docs.djangoproject.com/en/stable/ref/settings/#data-upload-max-memory-size ,
https://www.rfc-editor.org/rfc/rfc9110#name-idempotent-methods
