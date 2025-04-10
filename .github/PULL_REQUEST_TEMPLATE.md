# Summary of Changes

Added Pyright type checking execution to the CI gates. Here are the details of the implementation:
- Added `pyright` as a dependency in the `requirements/tests` file.
- Added new environments `pyright` and `pyright_tests` and a new job `run-pyright` to the file `.github/workflows/tests.yaml`.
- Added Pyright configuration section in `pyproject.toml` file, using pyright [diagnostic settings](https://github.com/microsoft/pyright/blob/main/docs/configuration.md#diagnostic-settings-defaults).
- Added testing functionality for Pyright in the `tox.ini` file.

# Related Issues

N/A

# Pull Request Checklist

This is just a reminder about the most common mistakes.  Please make sure that you tick all *appropriate* boxes.  But please read our [contribution guide](../CONTRIBUTING.md) at least once; it will save you a few review cycles!

If an item doesn't apply to your pull request, **check it anyway** to make it apparent that there's nothing to do.

- [x] Applied changes to both WSGI and ASGI code paths and interfaces (where applicable).
- [x] Added **tests** for changed code.
- [x] Prefixed code comments with GitHub nick and an appropriate prefix.
- [x] Coding style is consistent with the rest of the framework.
- [x] Updated **documentation** for changed code.
    - [x] Added docstrings for any new classes, functions, or modules.
    - [x] Updated docstrings for any modifications to existing code.
    - [x] Updated both WSGI and ASGI docs (where applicable).
    - [x] Added references to new classes, functions, or modules to the relevant RST file under `docs/`.
    - [x] Updated all relevant supporting documentation files under `docs/`.
    - [x] A copyright notice is included at the top of any new modules (using your own name or the name of your organization).
    - [x] Changed/added classes/methods/functions have appropriate `versionadded`, `versionchanged`, or `deprecated` [directives](http://www.sphinx-doc.org/en/stable/usage/restructuredtext/directives.html?highlight=versionadded#directive-versionadded).
- [x] Changes (and possible deprecations) have [towncrier](https://towncrier.readthedocs.io/en/latest/quickstart.html#creating-news-fragments) news fragments under `docs/_newsfragments/`, with the file name format `{issue_number}.{fragment_type}.rst`. (Run `towncrier --draft` to ensure it renders correctly.)

If you have *any* questions to *any* of the points above, just **submit and ask**! This checklist is here to *help* you, not to deter you from contributing!

*PR template inspired by the attrs project.*
