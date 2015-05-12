if [ "$JYTHON" = "true" ]; then
    $HOME/jython/bin/nosetests

    # Smoke test
    $HOME/jython/bin/jython falcon/bench/bench.py -t 1 -b falcon falcon-ext
else
    tox -e $TOX_ENV
fi
