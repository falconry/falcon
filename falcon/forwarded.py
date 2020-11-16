# Based on code from the aiohttp project, Copyright 2013-2017 by Nikolay Kim and
# Andrew Svetlov, with modifications for the Falcon project by Kurt Griffiths.
#
# See also:
#
#   https://github.com/aio-libs/aiohttp/blob/master/aiohttp/web_request.py
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

import re
import string

from falcon.util.uri import unquote_string


# '-' at the end to prevent interpretation as range in a char class
_TCHAR = string.digits + string.ascii_letters + r"!#$%&'*+.^_`|~-"

_TOKEN = r'[{tchar}]+'.format(tchar=_TCHAR)

# qdtext includes 0x5C to escape 0x5D ('\]')
# qdtext excludes obs-text (because obsoleted, and encoding not specified)
_QDTEXT = r'[{0}]'.format(
    r''.join(chr(c) for c in (0x09, 0x20, 0x21) + tuple(range(0x23, 0x7F))))

_QUOTED_PAIR = r'\\[\t !-~]'

_QUOTED_STRING = r'"(?:{quoted_pair}|{qdtext})*"'.format(
    qdtext=_QDTEXT, quoted_pair=_QUOTED_PAIR)

_FORWARDED_PAIR = (
    r'({token})=({token}|{quoted_string})'.format(
        token=_TOKEN,
        quoted_string=_QUOTED_STRING))

# same pattern as _QUOTED_PAIR but contains a capture group
_QUOTED_PAIR_REPLACE_RE = re.compile(r'\\([\t !-~])')

_FORWARDED_PAIR_RE = re.compile(_FORWARDED_PAIR)


class Forwarded:
    """Represents a parsed Forwarded header.

    (See also: RFC 7239, Section 4)

    Attributes:
        src (str): The value of the "for" parameter, or
            ``None`` if the parameter is absent. Identifies the
            node making the request to the proxy.
        dest (str): The value of the "by" parameter, or
            ``None`` if the parameter is absent. Identifies the
            client-facing interface of the proxy.
        host (str): The value of the "host" parameter, or
            ``None`` if the parameter is absent. Provides the host
            request header field as received by the proxy.
        scheme (str): The value of the "proto" parameter, or
            ``None`` if the parameter is absent. Indicates the
            protocol that was used to make the request to
            the proxy.
    """

    # NOTE(kgriffs): Use "client" since "for" is a keyword, and
    # "scheme" instead of "proto" to be consistent with the
    # falcon.Request interface.
    __slots__ = ('src', 'dest', 'host', 'scheme')

    def __init__(self):
        self.src = None
        self.dest = None
        self.host = None
        self.scheme = None


def _parse_forwarded_header(forwarded):
    """Parse the value of a Forwarded header.

    Makes an effort to parse Forwarded headers as specified by RFC 7239:

    - It checks that every value has valid syntax in general as specified
      in section 4: either a 'token' or a 'quoted-string'.
    - It un-escapes found escape sequences.
    - It does NOT validate 'by' and 'for' contents as specified in section
      6.
    - It does NOT validate 'host' contents (Host ABNF).
    - It does NOT validate 'proto' contents for valid URI scheme names.

    Arguments:
        forwarded (str): Value of a Forwarded header

    Returns:
        list: Sequence of Forwarded instances, representing each forwarded-element
        in the header, in the same order as they appeared in the header.
    """

    elements = []

    pos = 0
    end = len(forwarded)
    need_separator = False
    parsed_element = None

    while 0 <= pos < end:
        match = _FORWARDED_PAIR_RE.match(forwarded, pos)

        if match is not None:           # got a valid forwarded-pair
            if need_separator:
                # bad syntax here, skip to next comma
                pos = forwarded.find(',', pos)

            else:
                pos += len(match.group(0))
                need_separator = True

                name, value = match.groups()

                # NOTE(kgriffs): According to RFC 7239, parameter
                # names are case-insensitive.
                name = name.lower()

                if value[0] == '"':
                    value = unquote_string(value)

                # NOTE(kgriffs): If this is the first pair we've encountered
                # for this forwarded-element, initialize a new object.
                if not parsed_element:
                    parsed_element = Forwarded()

                if name == 'by':
                    parsed_element.dest = value
                elif name == 'for':
                    parsed_element.src = value
                elif name == 'host':
                    parsed_element.host = value
                elif name == 'proto':
                    # NOTE(kgriffs): RFC 7239 only requires that
                    # the "proto" value conform to the Host ABNF
                    # described in RFC 7230. The Host ABNF, in turn,
                    # does not require that the scheme be in any
                    # particular case, so we normalize it here to be
                    # consistent with the WSGI spec that *does*
                    # require the value of 'wsgi.url_scheme' to be
                    # either 'http' or 'https' (case-sensitive).
                    parsed_element.scheme = value.lower()

        elif forwarded[pos] == ',':      # next forwarded-element
            need_separator = False
            pos += 1

            # NOTE(kgriffs): It's possible that we arrive here without a
            # parsed element if the header is malformed.
            if parsed_element:
                elements.append(parsed_element)
                parsed_element = None

        elif forwarded[pos] == ';':      # next forwarded-pair
            need_separator = False
            pos += 1

        elif forwarded[pos] in ' \t':
            # Allow whitespace even between forwarded-pairs, though
            # RFC 7239 doesn't. This simplifies code and is in line
            # with Postel's law.
            pos += 1

        else:
            # bad syntax here, skip to next comma
            pos = forwarded.find(',', pos)

    # NOTE(kgriffs): Add the last forwarded-element, if any
    if parsed_element:
        elements.append(parsed_element)

    return elements
