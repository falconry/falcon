#!/usr/bin/env bash

FALCON_ROOT=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/../.." &> /dev/null && pwd )
MAILMAN_PATH=$FALCON_ROOT/.ecosystem/mailman

# TODO(vytas): Detect the latest version from git tags or PyPi JSON.
# NOTE(vytas): One approach: `curl -Ls https://pypi.org/pypi/mailman/json | jq -r .info.version`
# MAILMAN_VERSION=3.3.5

# Clean up in case we are running locally and not in CI
rm -rf $MAILMAN_PATH

mkdir -p .ecosystem
git clone --depth 100 https://gitlab.com/mailman/mailman.git/ $MAILMAN_PATH

# TODO(vytas): Enable version checking when a stable release's tests pass as-is.
#   At the time of writing, the latest version tag (3.3.5) has some failing tests.
cd $MAILMAN_PATH
# git checkout tags/$MAILMAN_VERSION

# NOTE(vytas): Patch tox.ini to introduce a new Falcon environment.
cat <<EOT >> tox.ini

[testenv:falcon-nocov]
basepython = python3.12
commands_pre =
    pip uninstall -y falcon
    pip install $FALCON_ROOT
EOT

# NOTE(vytas): The below test started failing on GitHub Actions:
#   '=?utf-8?b?QSBtdWx0aWxpbmUgWy4uLl0=?=' != 'A multiline [...]'
#   (but it works on other platforms).
sed -i s/test_uheader_multiline/skip_test_uheader_multiline/ \
    src/mailman/handlers/tests/test_cook_headers.py
