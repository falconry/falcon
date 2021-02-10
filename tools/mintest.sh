#!/usr/bin/env bash

# TODO(kgriffs): Revisit second half of 2021 to see if we still need to pin tox
#
#   See also: https://github.com/tox-dev/tox/issues/1777
#
pip install -U tox==3.20 coverage

rm -f .coverage.*

# NOTE(kgriffs): Do one at a time so we can just bail and not waste time
#   with the other envs which will also likely fail anyway.
tox -e pep8 && tox -e mypy && tox -e py35 && tox -e py38 && tox -e py38_sans_msgpack && tools/testing/combine_coverage.sh
