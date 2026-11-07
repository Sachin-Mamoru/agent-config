# Python performance around a Django app

## Profile first

```bash
python -X importtime -c "import myproject.wsgi" 2> imports.log        # slow startup/imports
python -m cProfile -o out.prof manage.py <command> ...                  # deterministic profile
python -c "import pstats; pstats.Stats('out.prof').sort_stats('cumulative').print_stats(25)"
py-spy top --pid <pid>          # sampling, attach to a live process (if installed)
py-spy record -o flame.svg --pid <pid>
```

Python 3.15 adds a built-in sampling profiler (`python -m profiling.sampling run|attach`,
PEP 799), and `cProfile` moves to `profiling.tracing` (the old name stays as an alias). These
exist only on 3.15+, so check `python -VV` before suggesting them. On older versions use
`cProfile` or `py-spy`.

Read `cumulative` for "which call path is slow" and `tottime` for "where CPU is actually burned".
In Django the top entries are usually database calls (go back to the ORM checks), serialization
of large payloads, or template/PDF/image work.

## I/O-bound or CPU-bound?

- Mostly waiting on DB, HTTP or storage: I/O-bound. Fix the number or size of calls first
  (batching, fewer round trips). Concurrency helps only when there are several *independent*
  waits.
- Mostly Python bytecode (parsing, maths, transforming big structures): CPU-bound. Fix the
  algorithm or data structure first, then vectorise or use a native library (NumPy, orjson,
  Polars, lxml).

## Picking a concurrency model

| Work | Tool | Note |
|---|---|---|
| A few independent blocking I/O calls in a sync view or task | `concurrent.futures.ThreadPoolExecutor` | Each thread that touches the ORM opens its own DB connection; close it (`connection.close()`) or use `close_old_connections` |
| Many concurrent network calls in async code | `asyncio` (`TaskGroup`, `httpx.AsyncClient`) | Django ORM calls from async code need the async ORM API (`aget`, `afilter`…) or `sync_to_async` |
| CPU-heavy pure Python | `ProcessPoolExecutor` / multiprocessing, or a worker queue | Pickling cost and memory per process; don't fork after DB connections are open |
| CPU-heavy numeric work | Native libraries (release the GIL internally) | Usually the biggest win |
| Latency-insensitive heavy work | Background worker | Doesn't make the work faster, only moves it off the request path; total CPU is the same |

## The GIL, accurately

- Standard CPython builds have a GIL: one thread runs Python bytecode at a time, so threads speed
  up I/O-bound work, not CPU-bound pure Python.
- Free-threaded CPython (PEP 703): experimental in 3.13, officially supported but **not the
  default** from 3.14 (PEP 779). It's a separate build (`python3.14t`). Check the build with
  `sysconfig.get_config_var("Py_GIL_DISABLED")` (or `python -VV`), and the runtime state with
  `sys._is_gil_enabled()`. C extensions without free-threading support re-enable the GIL at import.
- Don't recommend free-threading for a Django service unless the deployed interpreter is a
  free-threaded build and its C extensions (psycopg, lxml, numpy…) support it.

## Memory

`tracemalloc` (stdlib) for allocation snapshots. In Django, the classic causes are
evaluating a huge queryset (`list(qs)`, `len(qs)`), `DEBUG=True` accumulating
`connection.queries` in long-running processes, and building whole files in memory instead of
streaming (`StreamingHttpResponse`, `iterator()`).

Sources: https://docs.python.org/3/library/profile.html ,
https://docs.python.org/3/library/profiling.sampling.html (3.15+) ,
https://docs.python.org/3/howto/free-threading-python.html#identifying-free-threaded-python ,
https://docs.python.org/3/library/concurrent.futures.html ,
https://docs.python.org/3/howto/free-threading-python.html ,
https://peps.python.org/pep-0703/ , https://peps.python.org/pep-0779/ ,
https://docs.djangoproject.com/en/stable/topics/async/ ,
https://docs.python.org/3/library/tracemalloc.html
