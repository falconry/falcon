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

from http import cookies as http_cookies
import sys

# Hoist misc. utils
from falcon.util.misc import *  # NOQA
from falcon.util.structures import *  # NOQA
from falcon.util.sync import *  # NOQA
from falcon.util.time import *  # NOQA


# NOTE(kgriffs): Backport support for the new 'SameSite' attribute
#   for Python versions prior to 3.8. We do it this way because
#   SimpleCookie does not give us a simple way to specify our own
#   subclass of Morsel.
_reserved_cookie_attrs = http_cookies.Morsel._reserved  # type: ignore
if 'samesite' not in _reserved_cookie_attrs:  # pragma: no cover
    _reserved_cookie_attrs['samesite'] = 'SameSite'  # type: ignore


IS_64_BITS = sys.maxsize > 2**32

from falcon.util.reader import BufferedReader as _PyBufferedReader  # NOQA

try:
    from falcon.cyutil.reader import BufferedReader as _CyBufferedReader
except ImportError:
    _CyBufferedReader = None

# NOTE(vytas): Cythonized BufferedReader makes heavy use of Py_ssize_t which
#   would overflow on 32-bit systems with form parts larger than 2 GiB.
BufferedReader = (_CyBufferedReader or _PyBufferedReader) if IS_64_BITS else _PyBufferedReader

if sys.version_info >= (3, 7):
    # NOTE(caselit): __getattr__ support for modules was added only in py 3.7. Deprecating an import
    # on previous version is hard to do, so we are displaying the warning only on 3.7+
    def __getattr__(name):
        if name == 'json':
            import warnings
            import json  # NOQA
            from .deprecation import DeprecatedWarning

            warnings.warn('Importing json from "falcon.util" is deprecated.', DeprecatedWarning)
            return json
        from types import ModuleType
        # fallback to the default implementation
        mod = sys.modules[__name__]
        return ModuleType.__getattr__(mod, name)
else:
    import json  # NOQA
