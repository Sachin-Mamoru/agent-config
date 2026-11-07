# Tracing a Django/DRF request

Use this to answer "what actually runs for this request?" before changing anything.

## Finding the route

```bash
grep -rn "router.register\|path(\|re_path(" --include=urls.py .       # where it's wired
python manage.py show_urls 2>/dev/null | grep <fragment>                # if django-extensions is installed
```

- `router.register(r"orders", OrderViewSet, basename="order")` creates `orders/` (list/create)
  and `orders/{pk}/` (retrieve/update/partial_update/destroy) plus one route per `@action`.
  `basename` is required when the viewset has no `queryset` attribute.
- `@action(detail=True, url_path="cancel")` → `orders/{pk}/cancel/`; inside it `self.action == "cancel"`.
- Nested routers (drf-nested-routers or hand-rolled) pass parent ids as URL kwargs — check how
  the parent is resolved and **who validates access to it**.

## What runs, in order

1. **Django middleware** (`MIDDLEWARE`, top to bottom) — sessions, CSRF, and project middleware
   that often attaches tenant/org/workspace to `request`. Exceptions here never reach DRF.
2. **`APIView.dispatch()` → `initial()`**:
   - content negotiation and versioning (`request.version`)
   - `perform_authentication()` — authentication is lazy; it runs at the first `request.user`
     access. Each class in `authentication_classes` is tried in order; the first non-`None`
     result wins. A class that raises stops the chain.
   - `check_permissions()` — every class in `get_permissions()` must allow (`has_permission`).
   - `check_throttles()`
3. **Handler** — `list`/`create`/`retrieve`/… or the `@action` method.
4. **Generic views** (`GenericAPIView` / `ModelViewSet`):
   - `get_object()` = `filter_queryset(get_queryset())` → lookup by `lookup_field` →
     **404 if not in the queryset** → `check_object_permissions()`.
   - `list()` = `filter_queryset(get_queryset())` → `paginate_queryset()` → serializer
     (`many=True`). **No object permission check** happens for list items.
   - `create()` → `serializer.is_valid(raise_exception=True)` → `perform_create(serializer)`.
   - `update()` → `get_object()` → serializer with `instance` (`partial=True` for PATCH) →
     `perform_update(serializer)`.
5. **Exception handler** (`EXCEPTION_HANDLER`) turns `APIException`, `Http404`,
   `PermissionDenied` into responses. Unhandled exceptions become 500s.

## 401 / 403 / 404 cheat sheet

| Situation | Status |
|---|---|
| No or invalid credentials, permission denies, first auth class has `authenticate_header` (Token, Basic, most JWT/OAuth2 classes) | 401 with `WWW-Authenticate` |
| Same, but first auth class is `SessionAuthentication` (no header) | 403 |
| Authenticated but `has_permission` / `has_object_permission` denies | 403 |
| Object exists but is filtered out of `get_queryset()` | 404 (deliberate non-disclosure) |
| Custom code raises `NotFound` to hide existence | 404 |

## Choosing the hook

| You need to… | Override |
|---|---|
| Restrict rows by user/tenant, add `select_related`/`prefetch_related` | `get_queryset()` |
| Different serializer per action | `get_serializer_class()` (branch on `self.action`) |
| Pass extra context (request, tenant) to serializers | `get_serializer_context()` |
| Set server-owned fields on save | `perform_create()` / `perform_update()` → `serializer.save(field=value)` |
| Different permissions per action | `get_permissions()` or `@action(permission_classes=…)` — both **replace** the defaults |
| Custom lookup (slug, composite) | `lookup_field` / `lookup_url_kwarg`, or `get_object()` keeping the `check_object_permissions()` call |
| Operation that isn't CRUD | `@action` calling a service/model method |

Object permissions are **not** checked on `create` either, because `get_object()` isn't called.
Authorise the parent or target in the serializer (scoped related field) or in `perform_create()`.

Don't override `create()`/`update()` just to set a field — that's what `perform_*` is for.
When you do override `get_object()`, keep `self.check_object_permissions(self.request, obj)`.

## Ownership and tenant boundaries

- Scope **every** queryset by the tenant root (`organization=request.organization`, `owner=request.user`).
  A missing scope on one action is the classic IDOR.
- Scope **related-field querysets** in serializers too: a `PrimaryKeyRelatedField(queryset=Project.objects.all())`
  lets a caller attach another tenant's project by id. Restrict it in `__init__` or with a
  field class that reads the tenant from `self.context["request"]`.
- Nested resources: check access to the parent (from the URL) before touching children.
- Bulk endpoints: filter the id list with `filter(id__in=ids, <tenant scope>)` and decide
  explicitly what happens to ids that were filtered out.

Sources: https://www.django-rest-framework.org/api-guide/views/#api-policy-implementation-methods ,
https://www.django-rest-framework.org/api-guide/generic-views/#methods ,
https://www.django-rest-framework.org/api-guide/routers/ ,
https://www.django-rest-framework.org/api-guide/authentication/#unauthorized-and-forbidden-responses ,
https://docs.djangoproject.com/en/stable/topics/http/middleware/
