"""URI utilities.

This module provides utility functions to parse, encode, decode, and
otherwise manipulate a URI. These functions are not available directly
in the `falcon` module, and so must be explicitly imported::

    from falcon import uri

    name, port = uri.parse_host('example.org:8080')
"""

# NOTE(kgriffs): This module exists to make "import falcon.uri"
# work. Eventually we will remove the util module and flatten the
# falcon namespace, but in the meantime...

from falcon.util.uri import decode
from falcon.util.uri import encode
from falcon.util.uri import encode_check_escaped
from falcon.util.uri import encode_value
from falcon.util.uri import encode_value_check_escaped
from falcon.util.uri import parse_host
from falcon.util.uri import parse_query_string
from falcon.util.uri import unquote_string
