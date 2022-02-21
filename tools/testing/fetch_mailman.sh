#!/usr/bin/env bash

MAILMAN_PATH=.ecosystem/mailman

# TODO(vytas): Detect the latest version from git tags or PyPi JSON.
# NOTE(vytas): One approach: `curl -Ls https://pypi.org/pypi/mailman/json | jq -r .info.version`
# MAILMAN_VERSION=3.3.5

# Clean up in case we are running locally and not in CI
rm -rf $MAILMAN_PATH

mkdir -p .ecosystem
git clone https://gitlab.com/mailman/mailman.git/ $MAILMAN_PATH

# TODO(vytas): Enable version checking when a stable release's tests pass as-is.
#   At the time of writing, the latest version tag (3.3.5) has some failing tests.
# cd $MAILMAN_PATH
# git checkout tags/$MAILMAN_VERSION
