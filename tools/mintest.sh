#!/usr/bin/env bash

# TODO(vytas): unpin coverage to allow 5.x+ when coveralls supports it
# https://github.com/coveralls-clients/coveralls-python/issues/203
pip install -U tox "coverage < 5.0"

rm -f .coverage.*
tox -e pep8 && tox -e py38 && tools/testing/combine_coverage.sh
