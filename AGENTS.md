# Falcon Agent Guide

Read `CONTRIBUTING.md` first. Treat `pyproject.toml` and `tox.ini` as the
executable source of truth when prose and configuration differ. In accordance
with the "Use of LLMs" policy in `CONTRIBUTING.md`, carefully review and test
all generated changes.

## Repository map

- `falcon/app.py`, `falcon/request.py`, and `falcon/response.py` implement the
  WSGI flavor, as well as base behavior that `falcon/asgi/` subclasses for
  ASGI and WebSocket support. More shared behavior lives in modules such as
  `falcon/app_helpers.py`, `falcon/routing/`, `falcon/media/`, and
  `falcon/util/`.
- `falcon/testing/` contains public test helpers. Primary tests live in
  `tests/`, with ASGI-specific coverage in `tests/asgi/`. Tutorial and example
  suites have dedicated tox environments.
- `falcon/cyutil/*.pyx` contains optional Cython-optimized counterparts of
  pure Python modules such as `falcon/util/reader.py` and `falcon/util/uri.py`.
  When available, the optimized versions are selected at import time (in
  `falcon/util/uri.py`, `falcon/util/misc.py`, and -- for the buffered
  reader -- `falcon/util/__init__.py`). Preserve both modes when changing
  these paths, and use a Cython tox environment.
- Documentation is reStructuredText under `docs/`. Put runnable recipe snippets
  in `examples/recipes/`; documentation includes them with `literalinclude`.

## Change rules

- Keep patches narrow. Preserve Falcon's public API compatibility, HTTP/RFC
  correctness, and Python 3.9+ support on CPython and PyPy unless the task
  explicitly changes those contracts.
- Check both WSGI and ASGI surfaces when shared request, response, routing,
  middleware, media, error, or testing behavior changes. Add or update the
  corresponding tests; do not assume inheritance makes behavior identical.
- Maintain 100% branch coverage for changed behavior, including error and
  version-specific paths. Do not add production dependencies casually;
  `[project].dependencies` is currently empty.
- Treat request and response hot paths as performance-sensitive. Reuse existing
  helpers. When throughput or allocation behavior could change, benchmark with
  `tox -e py310_bench -- <falcon-bench args>`.
- Do not bulk-modernize `%` formatting in `falcon/`. `pyproject.toml`
  deliberately ignores Ruff's `UP030`, `UP031`, and `UP032` there pending
  inspection and benchmarks.

## Style

- Ruff targets Python 3.9, 88 columns, and single quotes.
- Public classes, attributes, methods, and functions require
  Napoleon/Google-style docstrings. Start immediately after the opening quotes
  with a roughly 70-character summary that ends in a period.
- Name caught exceptions `ex`. Limit single-character names to trivial indices
  and standard formulas.
- Format non-trivial tagged comments as
  `TODO|NOTE|PERF|APPSEC(<GitHub handle>):`. If the author's handle is
  unavailable, do not invent one and don't impersonate other users;
  avoid the tagged comment unless necessary.

## Verification

Run commands from the repository root. Start with the focused test, run only
affected specialized environments next, and reserve the complete `tox` gate
for broad or final validation.

- Prepare a development environment by installing the project in editable
  mode together with the test dependencies:
  `pip install -e . -r requirements/tests`.
- In a prepared development environment, get focused feedback with
  `pytest tests/test_<area>.py -k '<case>'` or
  `pytest tests/asgi/test_<area>.py -k '<case>'`.
- Run all Python tests and collect coverage data with `tox -e pytest`; check
  minimum-dependency compatibility with `tox -e mintest`; verify optional
  Cython behavior with a matching environment such as `tox -e py312_cython`.
- Check formatting and lint with `tox -e ruff,pep8,pep8-docstrings`. Apply
  formatting and safe fixes only with `tox -e reformat`.
- For typing changes, run `tox -e mypy,mypy_tests`. For documentation or
  docstring changes, run `tox -e docs`.
- Always finish with a plain `tox` run without arguments (or `tox -r` to
  recreate environments): the default env selection is the complete local
  gate, and it must pass together with the 100% combined coverage check
  before changes are handed over to the operator.
  Documentation-only changes may instead finish with `tox -e docs`.

## Documentation and changelog

- Update user and API documentation when behavior or public contracts change;
  build it with `tox -e docs`.
- Functionality changes require
  `docs/_newsfragments/{issue_number}.{fragment_type}.rst`. The exact fragment
  types are `breakingchange`, `newandimproved`, `bugfix`, and `misc`. Name the
  fragment after the issue the change closes; use the PR number itself only
  when no associated issue exists.
  `tox -e docs` renders pending fragments into the changelog; preview the
  result there.
- Never invent an issue or PR number. If none is available, report that the
  fragment cannot be named instead of creating a placeholder.
- For recipes, put executable code in `examples/recipes/`, include it from
  `docs/user/recipes/`, and add coverage in `tests/test_recipes.py` when
  practical.

## Operator boundaries

- Never create, submit, or open a GitHub pull request. Prepare the changes and
  verification evidence, then ask the human operator to open the pull request.
- Never tick, check, or otherwise complete a pull request checklist on the
  operator's behalf. The human operator must review the changes and complete
  every checklist item manually.

See `CONTRIBUTING.md` for commit-message format, full docstring markup rules,
review policy, and contributor conduct.
