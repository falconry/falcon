#!/usr/bin/env bash

tox -e py26,py27,py36,pep8 && tools/testing/combine_coverage.sh
