#!/usr/bin/env bash

# Fail on errors
set -e

_EXPECTED_VERSION_MIMEPARSE="1.6.0"

pip install --upgrade python-mimeparse

_VERSION_OUTPUT=$(pip show python-mimeparse | grep ^Version: )
if [[ $_VERSION_OUTPUT == "Version: $_EXPECTED_VERSION_MIMEPARSE" ]]; then
	echo "Latest version of python-mimeparse has not changed ($_EXPECTED_VERSION_MIMEPARSE)"
    exit 0
fi

echo "Latest version of python-mimeparse is newer than expected."
exit 1
