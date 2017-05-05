#!/usr/bin/env bash

if [ "$JYTHON" = "true" ]; then
    set -e

    $HOME/jython/bin/pytest tests

    # Smoke test
    $HOME/jython/bin/jython falcon/bench/bench.py -t 1 -b falcon falcon-ext
else
    tox
fi
