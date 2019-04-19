#!/usr/bin/env bash

pip install -U tox coverage

rm -f .coverage.*
tox -e pep8 && tox -e py37 && tools/testing/combine_coverage.sh
