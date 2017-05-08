#!/usr/bin/env bash

if [ "$JYTHON" = "true" ]; then
    tools/travis/install_jython2.7.sh

    # NOTE(kgriffs): Use an older version of requests to work around a
    # "method code too large" bug that is triggered starting with
    # requests 2.11.1 under Jython 2.7.0 (see also the related Jython
    # bug: http://bugs.jython.org/issue527524).
    $HOME/jython/bin/pip install https://github.com/kennethreitz/requests/archive/v2.11.0.zip
    $HOME/jython/bin/pip install -r requirements/tests

    # python-xdist is not compatible with Jython
    $HOME/jython/bin/pip uninstall -y pytest-xdist
else
    pip install tox coveralls
fi
