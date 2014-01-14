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

import re

import six

# NOTE(kgriffs): See also RFC 3986
_UNRESERVED = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789'
               '-._~')

# NOTE(kgriffs): See also RFC 3986
_DELIMITERS = ":/?#[]@!$&'()*+,;="
_ALL_ALLOWED = _UNRESERVED + _DELIMITERS

_HEX_DIGITS = '0123456789ABCDEFabcdef'

# NOTE(kgriffs): Match query string fields that have names that
# start with a letter.
_QS_PATTERN = re.compile(r'(?<![0-9])([a-zA-Z][a-zA-Z_0-9\-.]*)=([^&]+)')


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

This models urllib.parse.quote(safe="~").

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

# NOTE(kgriffs): This is actually covered, but not in py33; hence the pragma

if six.PY2:  # pragma: no cover

    # This map construction is based on urllib
    _HEX_TO_BYTE = dict((a + b, (chr(int(a + b, 16)), int(a + b, 16)))
                        for a in _HEX_DIGITS
                        for b in _HEX_DIGITS)

    def decode(encoded_uri):
        """Decodes percent-encoded characters in a URI or query string.

        This function models the behavior of urllib.parse.unquote_plus, but
        is faster. It is also more robust, in that it will decode escaped
        UTF-8 mutibyte sequences.

        Args:
            encoded_uri: An encoded URI (full or partial).

        Returns:
            A decoded URL. Will be of type `unicode` on Python 2 IFF the
            URL contained escaped non-ASCII characters, in which case UTF-8
            is assumed per RFC 3986.

        """

        decoded_uri = encoded_uri

        # PERF(kgriffs): Don't take the time to instantiate a new
        # string unless we have to.
        if '+' in decoded_uri:
            decoded_uri = decoded_uri.replace('+', ' ')

        # Short-circuit if we can
        if '%' not in decoded_uri:
            return decoded_uri

        # Convert to bytes because we are about to replace chars and we
        # don't want Python to mistakenly interpret any high bits.
        if not isinstance(decoded_uri, str):
            # NOTE(kgriffs): Clients should never submit a URI that has
            # unescaped non-ASCII chars in them, but just in case they
            # do, let's encode in a non-lossy format.
            decoded_uri = decoded_uri.encode('utf-8')

        only_ascii = True

        tokens = decoded_uri.split('%')
        decoded_uri = tokens[0]
        for token in tokens[1:]:
            char, byte = _HEX_TO_BYTE[token[:2]]
            decoded_uri += char + token[2:]

            if only_ascii:
                only_ascii = (byte <= 127)

        # PERF(kgriffs): Only spend the time to do this if there
        # were non-ascii bytes found in the string.
        if not only_ascii:
            decoded_uri = decoded_uri.decode('utf-8', 'replace')

        return decoded_uri

# NOTE(kgriffs): This is actually covered, but not in py2x; hence the pragma

else:  # pragma: no cover

    # This map construction is based on urllib
    _HEX_TO_BYTE = dict(((a + b).encode(), bytes([int(a + b, 16)]))
                        for a in _HEX_DIGITS
                        for b in _HEX_DIGITS)

    def _unescape(matchobj):
        # NOTE(kgriffs): Strip '%' and convert the hex number
        return _HEX_TO_BYTE[matchobj.group(0)[1:]]

    def decode(encoded_uri):
        """Decodes percent-encoded characters in a URI or query string.

        This function models the behavior of urllib.parse.unquote_plus,
        albeit in a faster, more straightforward manner.

        Args:
            encoded_uri: An encoded URI (full or partial).

        Returns:
            A decoded URL. If the URL contains escaped non-ASCII
            characters, UTF-8 is assumed per RFC 3986.

        """

        decoded_uri = encoded_uri

        # PERF(kgriffs): Don't take the time to instantiate a new
        # string unless we have to.
        if '+' in decoded_uri:
            decoded_uri = decoded_uri.replace('+', ' ')

        # Short-circuit if we can
        if '%' not in decoded_uri:
            return decoded_uri

        # NOTE(kgriffs): Clients should never submit a URI that has
        # unescaped non-ASCII chars in them, but just in case they
        # do, let's encode into a non-lossy format.
        decoded_uri = decoded_uri.encode('utf-8')

        # PERF(kgriffs): This was found to be faster than using
        # a regex sub call or list comprehension with a join.
        tokens = decoded_uri.split(b'%')
        decoded_uri = tokens[0]
        for token in tokens[1:]:
            decoded_uri += _HEX_TO_BYTE[token[:2]] + token[2:]

        # Convert back to str
        return decoded_uri.decode('utf-8', 'replace')


def parse_query_string(query_string):
    """Parse a query string into a dict

    Query string parameters are assumed to use standard form-encoding. Only
    parameters with values are parsed. for example, given "foo=bar&flag",
    this function would ignore "flag".

    Args:
        query_string: The query string to parse

    Returns:
        A dict containing (name, value) pairs, one per query parameter. Note
        that value will be a string, and that name is case-sensitive, both
        copied directly from the query string.

    Raises:
        TypeError: query_string was not a string or buffer

    """

    # PERF(kgriffs): A for loop is faster than using array or dict
    # comprehensions (tested under py27, py33). Go figure!
    params = {}
    for k, v in _QS_PATTERN.findall(query_string):
        params[k] = v

    return params
