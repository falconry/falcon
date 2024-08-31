## Release Manager's Guide

Release Process:

1. Bump version (including the suffix for pre-release, if applicable).
2. Update changelog and render towncrier fragments.
3. Release beta or rc.
4. Run benchmark and check for regressions.
5. Review and edit doc changes since the last release for clarity and consistency.
6. Publish final version and add a release note.
7. Run benchmark and update falconframework.org with latest numbers.
8. Announce the new version in Gitter channels and on the socials.
9. Improve this document.

### Bump version

Modify `falcon/version.py` if it has not been updated since the previous
release. Examine the rendered changelog to determine the appropriate SEMVER
field to modify.

Note that we have dropped `setup.cfg` altogether, so `__version__` in
`falcon/version.py` must contain the **whole version**
(including the previously separately managed `tag_build`), for instance:
```python
# Development version
__version__ = '4.0.0.dev1'

# First alpha
__version__ = '4.0.0a1'

# Release candidate
__version__ = '4.0.0rc1'

# Stable release
__version__ = '4.0.0'
```

Update changelog filename in `pyproject.toml` to suit.

### Update changelog and render towncrier fragments

If a changelog RST has not yet been created, add one under `docs/changes` using
the following template, and update the summary and changes to supported
platforms to suit:

```rst
Changelog for Falcon 4.0.1
==========================

Summary
-------

This is a minor point release to take care of a couple of bugs that we did
not catch for 4.0.0.


.. towncrier release notes start

Contributors to this Release
----------------------------

Many thanks to those who contributed to this bugfix release:

```

Otherwise, ensure the summary has been brought up to date; be sure to highlight
key changes in this release.

Next, update the contributors and render towncrier fragments by running:

```sh
$ tox -e changelog_release
```

Examine the updated RST as well as the rendered HTML docs and make any
adjustments as needed. On OS X it's as simple as:

```sh
$ open docs/_build/html/changes/index.html
```

Or on Linux:

```sh
$ xdg-open docs/_build/html/changes/index.html
```

If you need to go back and make any additional tweaks:

```sh
$ git restore docs/changes
```

Then re-run the `tox` command when you're ready for another
proofreading. Or if you just made a manual edit to the updated RST,
you can re-render the docs without overwriting the changelog RST:

```sh
$ tox -e docs
```

If all looks good, remove the rendered towncrier fragments from
`docs/_newsfragments` and then submit a PR containing the changes made so far.

Finally, merge the documentation PR and check that everything renders correctly
on https://falcon.readthedocs.io/. Note that if the release is not based on
`master` (or `main`), you may need to manually enable build on RtD for the
branch or tag in question.

### Release beta or rc

Be sure to install and test from PyPI as a sanity check afterwards. Fix docs,
performance regressions, and reported bugs (if any) and release additional
betas or release candidates.

### Run benchmark and check for regressions

TODO: Replace with CI gate

### Review and edit doc changes since the last release for clarity and consistency

### Publish final version and add a release note

Be sure to install and test from PyPI as a sanity check afterwards.

### Run benchmark and update falconframework.org with latest numbers

### Announce the new version in Gitter channels and on the socials

### Improve this document

If you find any inconsistencies, outdated notes or anything missing here, make
sure you improve this document for future releases!
