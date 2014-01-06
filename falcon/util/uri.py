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

if six.PY3:  # pragma nocover
    import urllib.parse as urllib  # pylint: disable=E0611
else:  # pragma nocover
    import urllib


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


def decode(uri):
    """Decode any percent-encoded characters in a URI or query string.

    Args:
        uri: An encoded URI (full or partial). If of type str on Python 2,
            UTF-8 is assumed.

    Returns:
        A decoded URL. Will be of type `unicode` on Python 2 IFF `uri`
        contains percent-encoded chars (in which case there is a chance
        they might contain multibyte Unicode sequences).

    """

    encoded_uri = uri

    #
    # TODO(kgriffs): urllib is broken when it comes to decoding
    # non-ASCII strings on Python 2. The problem is, if you pass
    # it a str type, it doesn't even try to decode the character
    # set. On the other hand, if you pass it a unicode type, urllib
    # simply decodes code points as latin1 (not exactly a sensible
    # default, eh?).
    #
    # So, we could just let urllib do its thing and after the fact
    # decode the result like so:
    #
    # if six.PY2 and isinstance(encoded_uri, str):  # pragma nocover
    #     encoded_uri = encoded_uri.decode('utf-8', 'replace')
    #
    # However, that adds several microseconds and will rarely be
    # needed by the caller who is probably just decoding a query
    # string, and it is not common to put non-ASCII characters in
    # a cloud API's query string (please contact me if I am wrong!).
    #

    # PERF(kgriffs): unquote_plus can do this, but if there are
    # *only* plusses in the string, no '%', we can save a lot of
    # time!
    if '+' in encoded_uri:
        encoded_uri = encoded_uri.replace('+', ' ')

    if '%' in encoded_uri:
        encoded_uri = urllib.unquote(encoded_uri)

        # PERF(kgriffs): Only spend the time to do this if there
        # were multibyte, UTF-8 encoded sequences that were
        # percent-encoded.
        if six.PY2 and isinstance(encoded_uri, str):  # pragma nocover
            for byte in bytearray(encoded_uri):
                if byte > 127:
                    encoded_uri = encoded_uri.decode('utf-8', 'replace')
                    break

    return encoded_uri
