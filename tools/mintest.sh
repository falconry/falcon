#!/usr/bin/env bash

pip install -U tox coverage

rm -f .coverage.*

# NOTE(kgriffs): Do one at a time so we can just bail and not waste time
#   with the other envs which will also likely fail anyway.
tox -e pep8 && tox -e mypy && tox -e py35 && tox -e py38 && tox -e py38_sans_msgpack && tools/testing/combine_coverage.sh
