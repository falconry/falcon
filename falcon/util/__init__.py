"""General utilities.

This package includes multiple modules that implement utility functions
and classes that are useful to both apps and the Falcon framework
itself.

All utilities in the `structures`, `misc`, and `time` modules are
imported directly into the front-door `falcon` module for convenience::

    import falcon

    now = falcon.http_now()

Conversely, the `uri` module must be imported explicitly::

    from falcon import uri

    some_uri = '...'
    decoded_uri = uri.decode(some_uri)

"""

import json  # NOQA
import sys

# Hoist misc. utils
from falcon.util.misc import *  # NOQA
from falcon.util.streams import BufferedStream as _PyBufferedStream
from falcon.util.structures import *  # NOQA
from falcon.util.time import *  # NOQA


IS_64_BITS = sys.maxsize > 2**32

try:
    from falcon.cyutil.streams import BufferedStream as _CyBufferedStream
except ImportError:
    _CyBufferedStream = None

# NOTE(vytas): Cythonized BufferedStream makes heavy use of Py_ssize_t which
#   would overflow on 32-bit systems with form parts larger than 2 GiB.
BufferedStream = (_CyBufferedStream or _PyBufferedStream) if IS_64_BITS else _PyBufferedStream
