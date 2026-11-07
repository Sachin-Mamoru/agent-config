# QuerySet evaluation, caching and the usual traps

## When a QuerySet hits the database

QuerySets are lazy. Building them (`filter`, `exclude`, `order_by`, `annotate`, `select_related`, …)
runs no SQL. They are **evaluated** by iteration, `list()`, `len()`, `bool()`/`if qs:`, `repr()`,
pickling, and slicing with a step. The first full evaluation fills the queryset's
**result cache**, and later iteration of the *same object* reuses it.

```python
qs = Order.objects.filter(customer=c)
for o in qs: ...          # 1 query, fills qs's cache
for o in qs: ...          # 0 queries — same object, cached
qs.filter(status="paid")  # NEW queryset → new query when evaluated; doesn't use qs's cache
Order.objects.filter(customer=c)[0]   # LIMIT 1 query; indexing an unevaluated qs never fills a cache
```

## `len()` vs `count()` vs `exists()`

| Call | Unevaluated queryset | Already evaluated |
|---|---|---|
| `len(qs)` | Fetches **all rows** into the cache, then counts | Uses the cache |
| `qs.count()` | `SELECT COUNT(*)` | Uses the cache, no query (documented) |
| `qs.exists()` | Cheap existence query | Uses the cache in practice (implementation, not documented) |
| `if qs:` | Fetches all rows | Uses the cache |

So: if you'll iterate the rows anyway, evaluate once and use `len()`/truthiness on the cache.
The optimisation guide warns that an extra `count()`/`exists()` before evaluating costs a query.
If you only need a number or a yes/no, use `count()`/`exists()`.

## `iterator()`

Streams rows and **does not fill the cache**. Use it for one pass over large result sets.
Calling it on an already-evaluated queryset re-runs the query. On PostgreSQL it uses a
server-side cursor. With `prefetch_related`, `chunk_size` is **required** (optional with a
deprecation warning in 4.1; an error since 5.0), and prefetching runs per chunk. Without
prefetching, the default chunk size is 2000. Server-side cursors and transaction-pooling
connection poolers (PgBouncer in transaction mode) don't mix; see
`DISABLE_SERVER_SIDE_CURSORS`.

## Fetch modes (Django 6.1+ only)

`QuerySet.fetch_mode()` controls what happens when an instance lazily loads a deferred field or
relation. For example, `FETCH_PEERS` loads it for all instances fetched together in one query.
It's useful for N+1s you can't fix at the queryset (templates, third-party code). Check the
installed version first; on older Django, fix it with `select_related`/`prefetch_related`.

## Relations: what each tool does

- `select_related("customer", "customer__account")` — SQL JOIN, forward FK / one-to-one only, one query.
- `prefetch_related("items")` — one extra query per relation (`WHERE order_id IN (...)`),
  joined in Python. Works for reverse FK and M2M.
- `Prefetch("items", queryset=Item.objects.filter(active=True).select_related("product"), to_attr="active_items")`
  — filters, orders or joins the prefetched set. With `to_attr` the result is a list on the instance.
- **Prefetch is invalidated by filtering afterwards**: `order.items.filter(active=True)` in a
  serializer issues a new query per order, so prefetch the filtered set with `Prefetch` instead.
  The same goes for `.exclude()`, `.order_by()`, `.annotate()` and other chaining. `.all()`,
  iteration, `.count()` and `.exists()` use the prefetched results. `.first()`/`.last()`
  re-query when the prefetched set has no ordering.
- `SerializerMethodField`s and `@property`s that touch relations are the usual hidden N+1s.
  Read them when counting queries.

## Aggregation correctness

Annotating over **two different multi-valued relations** joins both, which multiplies rows:

```python
Customer.objects.annotate(n_orders=Count("orders"), n_tickets=Count("tickets"))   # both inflated
```

- `Count("orders", distinct=True)` fixes counts, but there's no equivalent for `Sum`/`Avg` (distinct
  values would drop legitimately equal amounts).
- Correct pattern for sums: one subquery per relation.

```python
from django.db.models import OuterRef, Subquery, Sum, IntegerField
from django.db.models.functions import Coalesce

order_totals = (Order.objects.filter(customer=OuterRef("pk"))
                .values("customer").annotate(t=Sum("total")).values("t"))
Customer.objects.annotate(order_total=Coalesce(Subquery(order_totals), 0))
```

- `filter()` before vs after `annotate()` changes what's aggregated. Use
  `Count("orders", filter=Q(orders__status="paid"))` for conditional aggregates.
- `values("x").annotate(...)` groups by `x`. A model `Meta.ordering` can sneak extra GROUP BY
  columns in on older Django versions, so check the SQL.

## Writes

- `qs.update(...)` is one UPDATE, returns the number of matched rows, and skips `save()` and
  `pre_save`/`post_save` signals. It's often exactly right, but check that nothing relied on `save()`.
- `F("stock") - 1` makes the database do arithmetic, so there's no read-modify-write race. After
  `obj.save()` with an `F()` assignment: **before Django 6.0** (incl. 5.2 LTS) the attribute keeps
  the expression, and it's re-applied on every later `save()`, so call `refresh_from_db()`. **From
  6.0** the value is refreshed on save (no extra query on PostgreSQL).
- `bulk_create`/`bulk_update` skip `save()` and signals, and `bulk_update` is slow for very
  large batches. Use `batch_size`.

## Denormalisation trade-off

A stored counter or total (`order.items_count`) removes an aggregate from hot reads but adds a
write path that must stay correct under concurrency (`F()` updates in the same transaction,
or a periodic reconcile). Propose it only with measured read pressure, and name the write cost.

Sources: https://docs.djangoproject.com/en/stable/ref/models/querysets/#when-querysets-are-evaluated ,
https://docs.djangoproject.com/en/stable/topics/db/queries/#caching-and-querysets ,
https://docs.djangoproject.com/en/stable/ref/models/querysets/#iterator ,
https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-related ,
https://docs.djangoproject.com/en/stable/topics/db/aggregation/#combining-multiple-aggregations ,
https://docs.djangoproject.com/en/stable/ref/models/expressions/#avoiding-race-conditions-using-f ,
https://docs.djangoproject.com/en/stable/ref/models/expressions/#f-assignments-are-refreshed-after-model-save ,
https://docs.djangoproject.com/en/stable/topics/db/optimization/#don-t-overuse-contains-count-and-exists ,
https://docs.djangoproject.com/en/stable/ref/models/querysets/#fetch-mode ,
https://docs.djangoproject.com/en/stable/releases/5.0/#features-removed-in-5-0 ,
https://docs.djangoproject.com/en/stable/ref/databases/#transaction-pooling-server-side-cursors
