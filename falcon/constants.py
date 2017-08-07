HTTP_METHODS = (
    'CONNECT',
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
    'TRACE',
)

# NOTE(kgriffs): According to RFC 7159, most JSON parsers assume
# UTF-8 and so it is the recommended default charset going forward,
# and indeed, other charsets should not be specified to ensure
# maximum interoperability.
#
# TODO(kgriffs) In Falcon 2.0, omit the charset parameter
# below.
MEDIA_JSON = 'application/json; charset=UTF-8'

# NOTE(kgriffs): An internet media type for MessagePack has not
# yet been registered. 'application/x-msgpack' is commonly used,
# but the use of the 'x-' prefix is discouraged by RFC 6838.
MEDIA_MSGPACK = 'application/msgpack'

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

# NOTE(kgriffs): According to RFC 6838, most text media types should
# include the charset parameter.
MEDIA_HTML = 'text/html; charset=utf-8'
MEDIA_JS = 'text/javascript; charset=utf-8'
MEDIA_TEXT = 'text/plain; charset=utf-8'

MEDIA_JPEG = 'image/jpeg'
MEDIA_PNG = 'image/png'
MEDIA_GIF = 'image/gif'

DEFAULT_MEDIA_TYPE = MEDIA_JSON
