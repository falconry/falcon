from enum import auto
from enum import Enum
import os
import sys

__all__ = (
    'HTTP_METHODS',
    'WEBDAV_METHODS',
    'COMBINED_METHODS',
    'DEFAULT_MEDIA_TYPE',
    'MEDIA_BMP',
    'MEDIA_GIF',
    'MEDIA_HTML',
    'MEDIA_JPEG',
    'MEDIA_JS',
    'MEDIA_JSON',
    'MEDIA_MSGPACK',
    'MEDIA_MULTIPART',
    'MEDIA_PNG',
    'MEDIA_TEXT',
    'MEDIA_URLENCODED',
    'MEDIA_XML',
    'MEDIA_YAML',
    'SINGLETON_HEADERS',
    'WebSocketPayloadType',
)

PYPY = sys.implementation.name == 'pypy'
"""Evaluates to ``True`` when the current Python implementation is PyPy."""

PYTHON_VERSION = tuple(sys.version_info[:3])
"""Python version information triplet: (major, minor, micro)."""

FALCON_SUPPORTED = PYTHON_VERSION >= (3, 8, 0)
"""Whether this version of Falcon supports the current Python version."""

if not FALCON_SUPPORTED:  # pragma: nocover
    raise ImportError(
        'Falcon requires Python 3.8+. '
        '(Recent Pip should automatically pick a suitable Falcon version.)'
    )

ASGI_SUPPORTED = FALCON_SUPPORTED
"""Evaluates to ``True`` when ASGI is supported for the current Python version.

This constant is no longer referenced by the framework itself, and left for
compatibility with Falcon 3.x.
"""

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
    HTTP_METHODS + WEBDAV_METHODS + FALCON_CUSTOM_HTTP_METHODS + _META_METHODS
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

# NOTE(euj1n0ng): According to RFC 9239, Changed the intended usage of the
#   media type "text/javascript" from OBSOLETE to COMMON. Changed
#   the intended usage for all other script media types to obsolete.
MEDIA_JS = 'text/javascript'

# NOTE(kgriffs): According to RFC 6838, most text media types should
# include the charset parameter.
MEDIA_HTML = 'text/html; charset=utf-8'
MEDIA_TEXT = 'text/plain; charset=utf-8'

MEDIA_JPEG = 'image/jpeg'
MEDIA_PNG = 'image/png'
MEDIA_GIF = 'image/gif'
MEDIA_BMP = 'image/bmp'

DEFAULT_MEDIA_TYPE = MEDIA_JSON

# NOTE(kgriffs): We do not expect more than one of these in the request
SINGLETON_HEADERS = frozenset(
    [
        'content-length',
        'content-type',
        'cookie',
        'expect',
        'from',
        'host',
        'max-forwards',
        'referer',
        'user-agent',
    ]
)

# NOTE(vytas): We strip the preferred charsets from the default static file
#   type mapping as it is hard to make any assumptions without knowing which
#   files are going to be served. Moreover, the popular web servers (like
#   Nginx) do not try to guess either.
_DEFAULT_STATIC_MEDIA_TYPES = tuple(
    (ext, media_type.split(';', 1)[0])
    for ext, media_type in (
        ('.bmp', MEDIA_BMP),
        ('.gif', MEDIA_GIF),
        ('.htm', MEDIA_HTML),
        ('.html', MEDIA_HTML),
        ('.jpeg', MEDIA_JPEG),
        ('.jpg', MEDIA_JPEG),
        ('.js', MEDIA_JS),
        ('.json', MEDIA_JSON),
        ('.mjs', MEDIA_JS),
        ('.png', MEDIA_PNG),
        ('.txt', MEDIA_TEXT),
        ('.xml', MEDIA_XML),
        ('.yaml', MEDIA_YAML),
        ('.yml', MEDIA_YAML),
    )
)


class WebSocketPayloadType(Enum):
    """Enum representing the two possible WebSocket payload types."""

    TEXT = auto()
    BINARY = auto()
