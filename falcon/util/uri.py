"""Defines URI utilities

Copyright 2014 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import six


# NOTE(kgriffs): See also RFC 3986
_UNRESERVED = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789'
               '-._~')

# NOTE(kgriffs): See also RFC 3986
_DELIMITERS = ":/?#[]@!$&'()*+,;="

_ALL_ALLOWED = _UNRESERVED + _DELIMITERS


def _create_char_encoder(allowed_chars):

    lookup = {}

    for code_point in range(256):
        if chr(code_point) in allowed_chars:
            encoded_char = chr(code_point)
        else:
            encoded_char = '%{0:02X}'.format(code_point)

        # NOTE(kgriffs): PY2 returns str from uri.encode, while
        # PY3 returns a byte array.
        key = chr(code_point) if six.PY2 else code_point
        lookup[key] = encoded_char

    return lookup.__getitem__


def _create_str_encoder(is_value):

    allowed_chars = _UNRESERVED if is_value else _ALL_ALLOWED
    encode_char = _create_char_encoder(allowed_chars)

    def encoder(uri):
        # PERF(kgriffs): Very fast way to check, learned from urlib.quote
        if not uri.rstrip(allowed_chars):
            return uri

        # Convert to a byte array if it is not one already
        #
        # NOTE(kgriffs): Code coverage disabled since in Py3K the uri
        # is always a text type, so we get a failure for that tox env.
        if isinstance(uri, six.text_type):  # pragma no cover
            uri = uri.encode('utf-8')

        # Use our map to encode each char and join the result into a new uri
        #
        # PERF(kgriffs): map is faster than list comp on py27, but a tiny bit
        # slower on py33. Since we are already much faster than urllib on
        # py33, let's optimize for py27.
        return ''.join(map(encode_char, uri))

    return encoder


encode = _create_str_encoder(False)
encode.__name__ = 'encode'
encode.__doc__ = """Encodes a full or relative URI according to RFC 3986.

Escapes disallowed characters by percent-encoding them according
to RFC 3986.

This function is faster in the average case than the similar
`quote` function found in urlib. It also strives to be easier
to use by assuming a sensible default of allowed characters.

RFC 3986 defines a set of "unreserved" characters as well as a
set of "reserved" characters used as delimiters.

Args:
    uri: URI or part of a URI to encode. If this is a wide
        string (i.e., six.text_type), it will be encoded to
        a UTF-8 byte array and any multibyte sequences will
        be percent-encoded as-is.

Returns:
    An escaped version of `uri`, where all disallowed characters
    have been percent-encoded.

"""


encode_value = _create_str_encoder(True)
encode_value.name = 'encode_value'
encode_value.__doc__ = """Encodes a value string according to RFC 3986.

Escapes disallowed characters by percent-encoding them according
to RFC 3986.

This function is faster in the average case than the similar
`quote` function found in urlib. It also strives to be easier
to use by assuming a sensible default of allowed characters.

RFC 3986 defines a set of "unreserved" characters as well as a
set of "reserved" characters used as delimiters.

This function keeps things simply by lumping all reserved
characters into a single set of "delimiters", and everything in
that set is escaped.

Args:
    uri: Value to encode. It is assumed not to cross delimiter
        boundaries, and so any reserved URI delimiter characters
        included in it will be escaped. If `value` is a wide
        string (i.e., six.text_type), it will be encoded to
        a UTF-8 byte array and any multibyte sequences will
        be percent-encoded as-is.

Returns:
    An escaped version of `value`, where all disallowed characters
    have been percent-encoded.

"""
