#!/usr/bin/env bash

_EXPECTED_VERSION_MIMEPARSE="1.6.0"

_VERSION_OUTPUT=$(pip install python-mimeparse== 2>&1)
if [[ $_VERSION_OUTPUT == *", $_EXPECTED_VERSION_MIMEPARSE)"* ]]; then
	echo "Latest version of python-mimeparse has not changed ($_EXPECTED_VERSION_MIMEPARSE)"
    exit 0
fi

echo "Latest version of python-mimeparse is newer than expected."
exit 1
