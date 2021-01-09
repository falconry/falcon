from enum import Enum
import os
import sys


PYPY = (sys.implementation.name == 'pypy')
"""Evaluates to ``True`` when the current Python implementation is PyPy."""

ASGI_SUPPORTED = sys.version_info >= (3, 6)
"""Evaluates to ``True`` when ASGI is supported for the current Python version."""

# RFC 7231, 5789 methods
HTTP_METHODS = [
    'CONNECT',
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
    'TRACE',
]

# RFC 2518 and 4918 methods
WEBDAV_METHODS = [
    'CHECKIN',
    'CHECKOUT',
    'COPY',
    'LOCK',
    'MKCOL',
    'MOVE',
    'PROPFIND',
    'PROPPATCH',
    'REPORT',
    'UNCHECKIN',
    'UNLOCK',
    'UPDATE',
    'VERSION-CONTROL',
]

# if FALCON_CUSTOM_HTTP_METHODS is defined, treat it as a comma-
# delimited string of additional supported methods in this env.
FALCON_CUSTOM_HTTP_METHODS = [
    method.strip().upper()
    for method in os.environ.get('FALCON_CUSTOM_HTTP_METHODS', '').split(',')
    if method.strip() != ''
]

_META_METHODS = [
    'WEBSOCKET',
]

COMBINED_METHODS = (
    HTTP_METHODS +
    WEBDAV_METHODS +
    FALCON_CUSTOM_HTTP_METHODS +
    _META_METHODS
)

# NOTE(kgriffs): According to RFC 7159, most JSON parsers assume
# UTF-8 and so it is the recommended default charset going forward,
# and indeed, other charsets should not be specified to ensure
# maximum interoperability.
MEDIA_JSON = 'application/json'

# NOTE(kgriffs): An internet media type for MessagePack has not
# yet been registered. 'application/x-msgpack' is commonly used,
# but the use of the 'x-' prefix is discouraged by RFC 6838.
MEDIA_MSGPACK = 'application/msgpack'

MEDIA_MULTIPART = 'multipart/form-data'

MEDIA_URLENCODED = 'application/x-www-form-urlencoded'

# NOTE(kgriffs): An internet media type for YAML has not been
# registered. RoR uses 'application/x-yaml', but since use of
# 'x-' is discouraged by RFC 6838, we don't use it in Falcon.
#
# The YAML specification requires that parsers deduce the character
# encoding by examining the first few bytes of the document itself.
# Therefore, it does not make sense to include the charset in the
# media type string.
MEDIA_YAML = 'application/yaml'

# NOTE(kgriffs): According to RFC 7303, when the charset is
# omitted, preference is given to the encoding specified in the
# document itself (either via a BOM, or via the XML declaration). If
# the document does not explicitly specify the encoding, UTF-8 is
# assumed. We do not specify the charset here, because many parsers
# ignore it anyway and just use what is specified in the document,
# contrary to the RFCs.
MEDIA_XML = 'application/xml'

# NOTE(kgriffs): RFC 4329 recommends application/* over text/.
# futhermore, parsers are required to respect the Unicode
# encoding signature, if present in the document, and to default
# to UTF-8 when not present. Note, however, that implementations
# are not required to support anything besides UTF-8, so it is
# unclear how much utility an encoding signature (or the charset
# parameter for that matter) has in practice.
MEDIA_JS = 'application/javascript'

# NOTE(kgriffs): According to RFC 6838, most text media types should
# include the charset parameter.
MEDIA_HTML = 'text/html; charset=utf-8'
MEDIA_TEXT = 'text/plain; charset=utf-8'

MEDIA_JPEG = 'image/jpeg'
MEDIA_PNG = 'image/png'
MEDIA_GIF = 'image/gif'

DEFAULT_MEDIA_TYPE = MEDIA_JSON

# NOTE(kgriffs): We do not expect more than one of these in the request
SINGLETON_HEADERS = frozenset([
    'content-length',
    'content-type',
    'cookie',
    'expect',
    'from',
    'host',
    'max-forwards',
    'referer',
    'user-agent',
])

# NOTE(kgriffs): Special singleton to be used internally whenever using
#   None would be ambiguous.
_UNSET = object()

WebSocketPayloadType = Enum('WebSocketPayloadType', 'TEXT BINARY')
"""Enum representing the two possible WebSocket payload types."""
