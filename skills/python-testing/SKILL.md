---
name: python-testing
description: >
  How to run tests, check coverage, and run linting/pre-commit for fdm-be and udp-celery.
  Use when asked to run tests, check coverage, fix lint errors, or set up pre-commit hooks
  in either repo.
---

# Python Testing & Linting — fdm-be and udp-celery

Both repos use **uv** for dependency management, **pytest** for tests, and **ruff** for linting/formatting. AWS credentials are needed because tests may interact with S3/Secrets Manager.

---

## fdm-be

### Run all tests

```bash
cd ~/projects/pr/fdm-be
aws-vault exec developer -- uv run pytest tests/
```

> Excludes `tests/perf/` (Locust tests) — those use `run.sh` instead.

### Run a specific test file or test

```bash
aws-vault exec developer -- uv run pytest tests/unit/test_services/test_project_service.py
aws-vault exec developer -- uv run pytest tests/ -k "test_create_project"
```

### Run with coverage

```bash
aws-vault exec developer -- uv run pytest tests/ --cov=src --cov-report=term-missing
```

### Linting and formatting

```bash
# Lint (check only)
aws-vault exec developer -- uv run ruff check src tests

# Lint with auto-fix
aws-vault exec developer -- uv run ruff check --fix src tests

# Format
aws-vault exec developer -- uv run ruff format src tests

# Run all pre-commit hooks (what CI runs)
aws-vault exec developer -- uv run pre-commit run --all-files
```

### Install pre-commit hooks (once per clone)

```bash
aws-vault exec developer -- uv run pre-commit install
```

---

## udp-celery

### Run unit tests

```bash
cd ~/projects/pr/udp-celery
aws-vault exec developer -- uv run pytest tests/unit/
```

> Integration tests (`tests/integration/`) require Docker services — run separately.

### Run a specific test

```bash
aws-vault exec developer -- uv run pytest tests/unit/test_fdm/test_udp.py
aws-vault exec developer -- uv run pytest tests/unit/ -k "test_post_process"
```

### Run with coverage

```bash
aws-vault exec developer -- uv run pytest tests/unit/ --cov=src --cov-report=term-missing
```

### Coverage diff (PR helper)

```bash
# Compare coverage against develop branch
aws-vault exec developer -- python scripts/coverage_diff.py
```

### Linting and formatting

```bash
# Lint
aws-vault exec developer -- uv run ruff check src tests

# Lint with auto-fix
aws-vault exec developer -- uv run ruff check --fix src tests

# Format
aws-vault exec developer -- uv run ruff format src tests

# All pre-commit hooks
aws-vault exec developer -- uv run pre-commit run --all-files
```

### Install pre-commit hooks (once per clone)

```bash
aws-vault exec developer -- uv run pre-commit install
```

---

## Test writing conventions (both repos)

- One behaviour per test function — don't test multiple things together
- Naming: `test_<function>_<scenario>_<expected_outcome>`
  - e.g. `test_create_project_duplicate_name_raises_conflict`
- Use `AsyncMock` for async dependencies
- Mock at the boundary — mock repos in service tests, mock services in router tests
- All shared fixtures go in the existing `conftest.py` — never create a new one
- Use `pytest-asyncio` for async tests (`@pytest.mark.asyncio` or `asyncio_mode = "auto"` in config)

---

## Common pytest flags

| Flag | Use |
|------|-----|
| `-x` | Stop on first failure |
| `-v` | Verbose output |
| `-s` | Don't capture stdout (see print/logs) |
| `-k "pattern"` | Run only matching test names |
| `--tb=short` | Shorter tracebacks |
| `--no-header` | Cleaner output |
| `--cov=src --cov-report=term-missing` | Coverage with missing lines |
