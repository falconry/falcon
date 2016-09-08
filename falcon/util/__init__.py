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

# Hoist misc. utils
from falcon.util import structures
from falcon.util.misc import *  # NOQA
from falcon.util.time import *  # NOQA

CaseInsensitiveDict = structures.CaseInsensitiveDict
