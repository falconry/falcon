#!/usr/bin/env bash

set -e

pushd .ecosystem/hug
source .venv/bin/activate
python -m pytest tests
popd
