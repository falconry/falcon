# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""URI utilities.

This module provides utility functions to parse, encode, decode, and
otherwise manipulate a URI. These functions are not available directly
in the `falcon` module, and so must be explicitly imported::

    from falcon import uri

    name, port = uri.parse_host('example.org:8080')

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

_HEX_DIGITS = '0123456789ABCDEFabcdef'


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
    allowed_chars_plus_percent = allowed_chars + '%'
    encode_char = _create_char_encoder(allowed_chars)

    def encoder(uri):
        # PERF(kgriffs): Very fast way to check, learned from urlib.quote
        if not uri.rstrip(allowed_chars):
            return uri

        if not uri.rstrip(allowed_chars_plus_percent):
            # NOTE(kgriffs): There's a good chance the string has already
            # been escaped. Do one more check to increase our certainty.
            tokens = uri.split('%')
            for token in tokens[1:]:
                hex_octet = token[:2]

                if not len(hex_octet) == 2:
                    break

                if not (hex_octet[0] in _HEX_DIGITS and
                        hex_octet[1] in _HEX_DIGITS):
                    break
            else:
                # NOTE(kgriffs): All percent-encoded sequences were
                # valid, so assume that the string has already been
                # encoded.
                return uri

            # NOTE(kgriffs): At this point we know there is at least
            # one unallowed percent character. We are going to assume
            # that everything should be encoded. If the string is
            # partially encoded, the caller will need to normalize it
            # before passing it in here.

        # Convert to a byte array if it is not one already
        if isinstance(uri, six.text_type):
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

RFC 3986 defines a set of "unreserved" characters as well as a
set of "reserved" characters used as delimiters. This function escapes
all other "disallowed" characters by percent-encoding them.

Note:
    This utility is faster in the average case than the similar
    `quote` function found in ``urlib``. It also strives to be easier
    to use by assuming a sensible default of allowed characters.

Args:
    uri (str): URI or part of a URI to encode. If this is a wide
        string (i.e., ``six.text_type``), it will be encoded to
        a UTF-8 byte array and any multibyte sequences will
        be percent-encoded as-is.

Returns:
    str: An escaped version of `uri`, where all disallowed characters
    have been percent-encoded.

"""


encode_value = _create_str_encoder(True)
encode_value.name = 'encode_value'
encode_value.__doc__ = """Encodes a value string according to RFC 3986.

Disallowed characters are percent-encoded in a way that models
``urllib.parse.quote(safe="~")``. However, the Falcon function is faster
in the average case than the similar `quote` function found in urlib.
It also strives to be easier to use by assuming a sensible default
of allowed characters.

All reserved characters are lumped together into a single set of
"delimiters", and everything in that set is escaped.

Note:
    RFC 3986 defines a set of "unreserved" characters as well as a
    set of "reserved" characters used as delimiters.

Args:
    uri (str): URI fragment to encode. It is assumed not to cross delimiter
        boundaries, and so any reserved URI delimiter characters
        included in it will be escaped. If `value` is a wide
        string (i.e., ``six.text_type``), it will be encoded to
        a UTF-8 byte array and any multibyte sequences will
        be percent-encoded as-is.

Returns:
    str: An escaped version of `uri`, where all disallowed characters
    have been percent-encoded.

"""

if six.PY2:  # NOQA: C901 - Work around a bug in flake8 McCabe scoring

    # This map construction is based on urllib
    _HEX_TO_BYTE = dict((a + b, (chr(int(a + b, 16)), int(a + b, 16)))
                        for a in _HEX_DIGITS
                        for b in _HEX_DIGITS)

    def decode(encoded_uri):
        """Decodes percent-encoded characters in a URI or query string.

        This function models the behavior of `urllib.parse.unquote_plus`, but
        is faster. It is also more robust, in that it will decode escaped
        UTF-8 mutibyte sequences.

        Args:
            encoded_uri (str): An encoded URI (full or partial).

        Returns:
            str: A decoded URL. Will be of type ``unicode`` on Python 2 IFF the
            URL contained escaped non-ASCII characters, in which case
            UTF-8 is assumed per RFC 3986.

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
            token_partial = token[:2]
            try:
                char, byte = _HEX_TO_BYTE[token_partial]
            except KeyError:
                char, byte = '%', 0

            decoded_uri += char + (token[2:] if byte else token)
            only_ascii = only_ascii and (byte <= 127)

        # PERF(kgriffs): Only spend the time to do this if there
        # were non-ascii bytes found in the string.
        if not only_ascii:
            decoded_uri = decoded_uri.decode('utf-8', 'replace')

        return decoded_uri

else:

    # This map construction is based on urllib
    _HEX_TO_BYTE = dict(((a + b).encode(), bytes([int(a + b, 16)]))
                        for a in _HEX_DIGITS
                        for b in _HEX_DIGITS)

    def decode(encoded_uri):
        """Decodes percent-encoded characters in a URI or query string.

        This function models the behavior of `urllib.parse.unquote_plus`,
        albeit in a faster, more straightforward manner.

        Args:
            encoded_uri (str): An encoded URI (full or partial).

        Returns:
            str: A decoded URL. If the URL contains escaped non-ASCII
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
            token_partial = token[:2]
            try:
                decoded_uri += _HEX_TO_BYTE[token_partial] + token[2:]
            except KeyError:
                # malformed percentage like "x=%" or "y=%+"
                decoded_uri += b'%' + token

        # Convert back to str
        return decoded_uri.decode('utf-8', 'replace')


def parse_query_string(query_string, keep_blank_qs_values=False,
                       parse_qs_csv=True):
    """Parse a query string into a dict.

    Query string parameters are assumed to use standard form-encoding. Only
    parameters with values are returned. For example, given 'foo=bar&flag',
    this function would ignore 'flag' unless the `keep_blank_qs_values` option
    is set.

    Note:
        In addition to the standard HTML form-based method for specifying
        lists by repeating a given param multiple times, Falcon supports
        a more compact form in which the param may be given a single time
        but set to a ``list`` of comma-separated elements (e.g., 'foo=a,b,c').

        When using this format, all commas uri-encoded will not be treated by
        Falcon as a delimiter. If the client wants to send a value as a list,
        it must not encode the commas with the values.

        The two different ways of specifying lists may not be mixed in
        a single query string for the same parameter.

    Args:
        query_string (str): The query string to parse.
        keep_blank_qs_values (bool): Set to ``True`` to return fields even if
            they do not have a value (default ``False``). For comma-separated
            values, this option also determines whether or not empty elements
            in the parsed list are retained.
        parse_qs_csv: Set to ``False`` in order to disable splitting query
            parameters on ``,`` (default ``True``). Depending on the user agent,
            encoding lists as multiple occurrences of the same parameter might
            be preferable. In this case, setting `parse_qs_csv` to ``False``
            will cause the framework to treat commas as literal characters in
            each occurring parameter value.

    Returns:
        dict: A dictionary of (*name*, *value*) pairs, one per query
        parameter. Note that *value* may be a single ``str``, or a
        ``list`` of ``str``.

    Raises:
        TypeError: `query_string` was not a ``str``.

    """

    params = {}

    # PERF(kgriffs): This was found to be faster than using a regex, for
    # both short and long query strings. Tested on both CPython 2.7 and 3.4,
    # and on PyPy 2.3.
    for field in query_string.split('&'):
        k, _, v = field.partition('=')
        if not (v or keep_blank_qs_values):
            continue

        # Note(steffgrez): Falcon first decode name parameter for handle
        # utf8 character.
        k = decode(k)

        # NOTE(steffgrez): Falcon decode value at the last moment. So query
        # parser won't mix up between percent-encoded comma (as value) and
        # comma-separated list (as reserved character for sub-delimiter)
        if k in params:
            # The key was present more than once in the POST data.  Convert to
            # a list, or append the next value to the list.
            old_value = params[k]
            if isinstance(old_value, list):
                old_value.append(decode(v))
            else:
                params[k] = [old_value, decode(v)]

        else:
            if parse_qs_csv and ',' in v:
                # NOTE(kgriffs): Falcon supports a more compact form of
                # lists, in which the elements are comma-separated and
                # assigned to a single param instance. If it turns out that
                # very few people use this, it can be deprecated at some
                # point.
                v = v.split(',')

                if not keep_blank_qs_values:
                    # NOTE(kgriffs): Normalize the result in the case that
                    # some elements are empty strings, such that the result
                    # will be the same for 'foo=1,,3' as 'foo=1&foo=&foo=3'.
                    params[k] = [decode(element) for element in v if element]
                else:
                    params[k] = [decode(element) for element in v]
            else:
                params[k] = decode(v)

    return params


def parse_host(host, default_port=None):
    """Parse a canonical 'host:port' string into parts.

    Parse a host string (which may or may not contain a port) into
    parts, taking into account that the string may contain
    either a domain name or an IP address. In the latter case,
    both IPv4 and IPv6 addresses are supported.

    Args:
        host (str): Host string to parse, optionally containing a
            port number.
        default_port (int, optional): Port number to return when
            the host string does not contain one (default ``None``).

    Returns:
        tuple: A parsed (*host*, *port*) tuple from the given
        host string, with the port converted to an ``int``.
        If the host string does not specify a port, `default_port` is
        used instead.

    """

    # NOTE(kgriff): The value from the Host header may
    # contain a port, so check that and strip it if
    # necessary. This is complicated by the fact that
    # a hostname may be specified either as an IP address
    # or as a domain name, and in the case of IPv6 there
    # may be multiple colons in the string.

    if host.startswith('['):
        # IPv6 address with a port
        pos = host.rfind(']:')
        if pos != -1:
            return (host[1:pos], int(host[pos + 2:]))
        else:
            return (host[1:-1], default_port)

    pos = host.rfind(':')
    if (pos == -1) or (pos != host.find(':')):
        # Bare domain name or IP address
        return (host, default_port)

    # NOTE(kgriffs): At this point we know that there was
    # only a single colon, so we should have an IPv4 address
    # or a domain name plus a port
    name, _, port = host.partition(':')
    return (name, int(port))


def unquote_string(quoted):
    """Unquote an RFC 7320 "quoted-string".

    Args:
        quoted (str): Original quoted string

    Returns:
        str: unquoted string

    Raises:
        TypeError: `quoted` was not a ``str``.
    """

    if len(quoted) < 2:
        return quoted
    elif quoted[0] != '"' or quoted[-1] != '"':
        # return original one, prevent side-effect
        return quoted

    tmp_quoted = quoted[1:-1]

    # PERF(philiptzou): Most header strings don't contain "quoted-pair" which
    # defined by RFC 7320. We use this little trick (quick string search) to
    # speed up string parsing by preventing unnecessary processes if possible.
    if '\\' not in tmp_quoted:
        return tmp_quoted
    elif r'\\' not in tmp_quoted:
        return tmp_quoted.replace('\\', '')
    else:
        return '\\'.join([q.replace('\\', '')
                          for q in tmp_quoted.split(r'\\')])
