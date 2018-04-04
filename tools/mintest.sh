#!/usr/bin/env bash

rm -f .coverage.*
tox -e py27,py36,pep8 && tools/testing/combine_coverage.sh
