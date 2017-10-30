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

"""Cookie parsing utility.

This module provides a utility function to parse cookies and is
a refactored version of the cpython 3.7 cookies library. We have
removed functionality that we don't use related to setting cookies
in order to speed up performance for the falcon framework. This
function is not available directly in the `falcon` module and so
must be explicitly imported:

    from falcon.util.cookies import parse_cookies

"""

import re
import string

_LegalKeyChars = r"\w\d!#%&'~_`><@,:/\$\*\+\-\.\^\|\)\(\?\}\{\="
_LegalValueChars = _LegalKeyChars + r'\[\]'
_CookiePattern = re.compile(
    r'(?x)'                              # This is a Verbose pattern
    r'\s*'                               # Optional whitespace at start of cookie
    r'(?P<key>'                          # Start of group 'key'
    '[' + _LegalKeyChars + ']+?'  # Any word of at least one letter, nongreedy
    r')'                                 # End of group 'key'
    r'('                                 # Optional group: there may not be a value.
    r'\s*=\s*'                           # Equal Sign
    r'(?P<val>'                          # Start of group 'val'
    r'"(?:[^\\"]|\\.)*"'                 # Any doublequoted string
    r'|'                                 # or
    r'\w{3},\s[\s\w\d-]{9,11}\s[\d:]{8}\sGMT'  # Special case for "expires" attr
    r'|'                                 # or
    '[' + _LegalValueChars + ']*'        # Any word or empty string
    r')'                                 # End of group 'val'
    r')?'                                # End of optional value group
    r'\s*'                               # Any number of spaces.
    r'(\s+|;|$)'                         # Ending either at space, semicolon, or EOS.
)

# RFC 2109 lists these attributes as reserved:
#   path       comment         domain
#   max-age    secure      version
#
# For historical reasons, these attributes are also reserved:
#   expires
#
# This is an extension from Microsoft:
#   httponly
#
# This dictionary provides a mapping from the lowercase
# variant on the left to the appropriate traditional
# formatting on the right.
_reserved = {
    'expires': 'expires',
    'path': 'Path',
    'comment': 'Comment',
    'domain': 'Domain',
    'max-age': 'Max-Age',
    'secure': 'Secure',
    'httponly': 'HttpOnly',
    'version': 'Version',
}
_flags = {'secure', 'httponly'}


def parse_cookies(cookie_header):
    """Parses a cookie header string and returns a dict

    This function parses each cookie individually and discards
    any cookies that do not conform to the following specification.

    KEY=VALUE;

    Keys may contain any letters, digits, or the following
    additional characters

    !#$%&'*+-.^_`|~:

    Values may contain the same set of characters as keys with the
    additional characters

    {}[]()<>@,/=

    Args:
        cookie_header (str): Cookie headers
    """

    i = 0                           # Our starting point
    n = len(cookie_header)          # Length of string
    parsed_cookies = {}             # Parsed cookies to return {key: val,}

    while 0 <= i < n:
        # Start looking for a cookie
        match = _CookiePattern.match(cookie_header, i)
        if not match:
            break          # No more cookies

        key, value = match.group('key'), match.group('val')
        i = match.end(0)

        # Parse the key, value in case it's metainfo
        if key[0] == '$':
            # NOTE(santeyio): from cpython 3.7 docs:
            # We ignore attributes which pertain to the cookie
            # mechanism as a whole, such as "$Version".
            # See RFC 2965. (Does anyone care?)
            continue
        elif key.lower() in _reserved:
            if value is None:
                if key.lower() in _flags:
                    parsed_cookies[key] = True
            else:
                parsed_cookies[key] = _unquote(value)
        # make sure final key doesn't contain illegal chars, skip if it does
        elif not _is_legal_key(key):
            continue
        # If there's no value it's an invalid cookie, skip it
        elif value is not None:
            parsed_cookies[key] = value

    return parsed_cookies


_OctalPatt = re.compile(r'\\[0-3][0-7][0-7]')
_QuotePatt = re.compile(r'[\\].')
_nulljoin = ''.join


# NOTE(santeyio): This method is taken directly from the python 3.7
# library. Reserved key values for cookie headers can contain ASCII
# encoded characters in double quotes. This method removes double quotes
# and converts ASCII codes to their character values.
def _unquote(str):
    # If there aren't any doublequotes,
    # then there can't be any special characters.  See RFC 2109.
    if str is None or len(str) < 2:
        return str
    if str[0] != '"' or str[-1] != '"':
        return str

    # We have to assume that we must decode this string.

    # Remove the "s
    str = str[1:-1]

    # Check for special sequences.  Examples:
    #    \012 --> \n
    #    \"   --> "
    #
    i = 0
    n = len(str)
    res = []
    while 0 <= i < n:
        o_match = _OctalPatt.search(str, i)
        q_match = _QuotePatt.search(str, i)
        if not o_match and not q_match:            # Neither matched
            res.append(str[i:])
            break
        # else:
        j = k = -1
        if o_match:
            j = o_match.start(0)
        if q_match:
            k = q_match.start(0)
        if q_match and (not o_match or k < j):     # QuotePatt matched
            res.append(str[i:k])
            res.append(str[k + 1])
            i = k + 2
        else:                                      # OctalPatt matched
            res.append(str[i:j])
            res.append(chr(int(str[j + 1:j + 4], 8)))
            i = j + 4
    return _nulljoin(res)


def _is_legal_key(key):
    # NOTE(santeyio): This is in place of re.fullmatch() (added in python 3.4)
    # for backwards compatibility with python 2
    _legal_chars = string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~:"
    r = '[%s]+' % re.escape(_legal_chars)
    return re.match('(?:' + r + r')\Z', key, 0)
