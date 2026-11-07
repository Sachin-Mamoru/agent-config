# Concurrency patterns with code

Model names are illustrative. Adapt them to the project's models, services and exceptions.

## One-shot state transition (preferred when the decision fits in a WHERE clause)

```python
CANCELLABLE = (Order.Status.PENDING, Order.Status.PAID)

def cancel_order(order_id: int, user) -> Order:
    updated = (Order.objects
               .filter(pk=order_id, owner=user, status__in=CANCELLABLE)
               .update(status=Order.Status.CANCELLED, cancelled_at=timezone.now()))
    if updated == 0:
        order = Order.objects.filter(pk=order_id, owner=user).first()
        if order is None:
            raise NotFound()                       # not yours or doesn't exist → 404
        raise Conflict(f"cannot cancel from {order.status}")   # → 409
    return Order.objects.get(pk=order_id)
```

One statement, so there's no race: of two concurrent cancels, PostgreSQL makes the second wait,
re-checks its WHERE on the updated row, and matches 0 rows. Caveat: `update()` skips `save()`
and signals. If cancelling has side effects (refund, email), use the locked variant or call
them explicitly after the update succeeded.

## Read-decide-write with a row lock

```python
@transaction.atomic
def cancel_order(order_id: int, user) -> Order:
    order = (Order.objects.select_for_update()
             .filter(owner=user).get(pk=order_id))      # DoesNotExist → 404
    if order.status not in CANCELLABLE:
        raise Conflict(...)
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "cancelled_at"])
    Refund.objects.create(order=order, amount=order.total)
    transaction.on_commit(lambda: notify_cancelled.delay(order.pk))   # after commit only
    return order
```

- `select_for_update()` raises `TransactionManagementError` outside a transaction.
- `select_for_update()` with `select_related()` across a nullable relation raises
  `NotSupportedError` ("FOR UPDATE cannot be applied to the nullable side of an outer join").
  The documented fix is to exclude the nulls (`.exclude(customer=None)`), or don't
  `select_related` that relation in the locking query. `of=(...)` chooses which tables are locked.
- Options: `nowait=True` (error instead of waiting), `skip_locked=True` (skip locked rows; not
  combinable with `nowait`), `no_key=True` (PostgreSQL `FOR NO KEY UPDATE`, weaker lock that
  doesn't block FK inserts).
- Don't call the payment provider inside this block. Record a "refund pending" row and let a
  task do the external call. Locks are held until commit.

In the view or `@action`, map `Conflict` to 409 with the project's exception type, and keep
`get_queryset()` scoping so other users' orders are 404.

## Counters and balances

```python
Product.objects.filter(pk=pid, stock__gte=qty).update(stock=F("stock") - qty)   # 0 rows → insufficient stock

class Meta:
    constraints = [models.CheckConstraint(condition=Q(stock__gte=0), name="stock_non_negative")]
```

(`CheckConstraint(condition=...)` is the Django 5.1+ spelling; older versions use `check=`.
Check the installed version.)

## Dedup and "only one" via constraints

```python
class Meta:
    constraints = [models.UniqueConstraint(fields=["tenant", "external_id"], name="uniq_import_per_tenant")]

try:
    with transaction.atomic():                       # savepoint, so the outer transaction survives
        Import.objects.create(tenant=t, external_id=eid, ...)
except IntegrityError:
    return Import.objects.get(tenant=t, external_id=eid)   # already done → idempotent result
```

`get_or_create` does the same dance internally, but it still needs the unique constraint to be
race-safe.

## Work queue claimed by many workers

```python
with transaction.atomic():
    batch = list(Job.objects.select_for_update(skip_locked=True)
                 .filter(status="pending").order_by("id")[:50])
    Job.objects.filter(pk__in=[j.pk for j in batch]).update(status="running", started_at=now())
# process outside the lock; write results with conditional updates
```

## Testing a real race (PostgreSQL)

```python
class TestCancelRace(TransactionTestCase):
    def test_only_one_cancel_wins(self):
        order = make_order(status="paid")
        barrier, results = threading.Barrier(2), []

        def attempt():
            try:
                barrier.wait()
                cancel_order(order.pk, order.owner)
                results.append("ok")
            except Conflict:
                results.append("conflict")
            finally:
                connection.close()

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        [t.start() for t in threads]; [t.join() for t in threads]
        self.assertCountEqual(results, ["ok", "conflict"])
        self.assertEqual(Refund.objects.filter(order=order).count(), 1)
```

`TestCase` wraps each test in one transaction on one connection, so it can't show a race and
never commits (`on_commit` callbacks need `captureOnCommitCallbacks(execute=True)` there).
Races need `TransactionTestCase` and a real PostgreSQL. Tag such tests if the project separates
slow tests.

Sources: https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update ,
https://docs.djangoproject.com/en/stable/ref/models/querysets/#update ,
https://docs.djangoproject.com/en/stable/topics/db/transactions/#controlling-transactions-explicitly ,
https://docs.djangoproject.com/en/stable/ref/models/constraints/#checkconstraint ,
https://docs.djangoproject.com/en/stable/topics/testing/tools/#transactiontestcase ,
https://www.postgresql.org/docs/current/transaction-iso.html#XACT-READ-COMMITTED
