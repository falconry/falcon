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

"""Utilities for the Request class."""

import io
import re

from falcon.util import ETag
from falcon.util.compat import http_cookies

# https://tools.ietf.org/html/rfc6265#section-4.1.1
#
# NOTE(kgriffs): Fortunately we don't have to worry about code points in
#   header strings outside the range 0x0000 - 0x00FF per PEP 3333
#   (see also: https://www.python.org/dev/peps/pep-3333/#unicode-issues)
#
_COOKIE_NAME_RESERVED_CHARS = re.compile('[\x00-\x1F\x7F-\xFF()<>@,;:\\\\"/[\\]?={} \x09]')

# NOTE(kgriffs): strictly speaking, the weakness indicator is
#   case-sensitive, but this wasn't explicit until RFC 7232
#   so we allow for both. We also require quotes because that's
#   been standardized since 1999, and it makes the regex simpler
#   and more performant.
_ENTITY_TAG_PATTERN = re.compile(r'([Ww]/)?"([^"]*)"')


def parse_cookie_header(header_value):
    """Parse a Cookie header value into a dict of named values.

    (See also: RFC 6265, Section 5.4)

    Args:
        header_value (str): Value of a Cookie header

    Returns:
        dict: Map of cookie names to a list of all cookie values found in the
        header for that name. If a cookie is specified more than once in the
        header, the order of the values will be preserved.
    """

    # See also:
    #
    #   https://tools.ietf.org/html/rfc6265#section-5.4
    #   https://tools.ietf.org/html/rfc6265#section-4.1.1
    #

    cookies = {}

    for token in header_value.split(';'):
        name, __, value = token.partition('=')

        # NOTE(kgriffs): RFC6265 is more strict about whitespace, but we
        # are more lenient here to better handle old user agents and to
        # mirror Python's standard library cookie parsing behavior
        name = name.strip()
        value = value.strip()

        # NOTE(kgriffs): Skip malformed cookie-pair
        if not name:
            continue

        # NOTE(kgriffs): Skip cookies with invalid names
        if _COOKIE_NAME_RESERVED_CHARS.search(name):
            continue

        # NOTE(kgriffs): To maximize compatibility, we mimic the support in the
        # standard library for escaped characters within a double-quoted
        # cookie value according to the obsolete RFC 2109. However, we do not
        # expect to see this encoding used much in practice, since Base64 is
        # the current de-facto standard, as recommended by RFC 6265.
        #
        # PERF(kgriffs): These checks have been hoisted from within _unquote()
        # to avoid the extra function call in the majority of the cases when it
        # is not needed.
        if len(value) > 2 and value[0] == '"' and value[-1] == '"':
            value = http_cookies._unquote(value)

        # PERF(kgriffs): This is slightly more performant as
        # compared to using dict.setdefault()
        if name in cookies:
            cookies[name].append(value)
        else:
            cookies[name] = [value]

    return cookies


def header_property(wsgi_name):
    """Create a read-only header property.

    Args:
        wsgi_name (str): Case-sensitive name of the header as it would
            appear in the WSGI environ ``dict`` (i.e., 'HTTP_*')

    Returns:
        A property instance than can be assigned to a class variable.

    """

    def fget(self):
        try:
            return self.env[wsgi_name] or None
        except KeyError:
            return None

    return property(fget)


# NOTE(kgriffs): Going forward we should privatize helpers, as done here. We
#   can always move this over to falcon.util if we decide it would be
#   more generally useful to app developers.
def _parse_etags(etag_str):
    """Parse a string containing one or more HTTP entity-tags.

    The string is assumed to be formatted as defined for a precondition
    header, and may contain either a single ETag, or multiple comma-separated
    ETags. The string may also contain a '*' character, in order to indicate
    that any ETag should match the precondition.

    (See also: RFC 7232, Section 3)

    Args:
        etag_str (str): An ASCII header value to parse ETags from. ETag values
            within may be prefixed by ``W/`` to indicate that the weak comparison
            function should be used.

    Returns:
        list: A list of unquoted ETags or ``['*']`` if all ETags should be
        matched. If the string to be parse is empty, or contains only
        whitespace, ``None`` will be returned instead.

    """

    etag_str = etag_str.strip()
    if not etag_str:
        return None

    if etag_str == '*':
        return [etag_str]

    if ',' not in etag_str:
        return [ETag.loads(etag_str)]

    etags = []

    # PERF(kgriffs): Parsing out the weak string like this turns out to be more
    #   performant than grabbing the entire entity-tag and passing it to
    #   ETag.loads(). This is also faster than parsing etag_str manually via
    #   str.find() and slicing.
    for weak, value in _ENTITY_TAG_PATTERN.findall(etag_str):
        t = ETag(value)
        t.is_weak = bool(weak)
        etags.append(t)

    # NOTE(kgriffs): Normalize a string with only whitespace and commas
    #   to None, since it is like a list of individual ETag headers that
    #   are all set to nothing, and so therefore basically should be
    #   treated as not having been set in the first place.
    return etags or None


class BoundedStream(io.IOBase):
    """Wrap *wsgi.input* streams to make them more robust.

    ``socket._fileobject`` and ``io.BufferedReader`` are sometimes used
    to implement *wsgi.input*. However, app developers are often burned
    by the fact that the `read()` method for these objects block
    indefinitely if either no size is passed, or a size greater than
    the request's content length is passed to the method.

    This class normalizes *wsgi.input* behavior between WSGI servers
    by implementing non-blocking behavior for the cases mentioned
    above.

    Args:
        stream: Instance of ``socket._fileobject`` from
            ``environ['wsgi.input']``
        stream_len: Expected content length of the stream.

    """

    def __init__(self, stream, stream_len):
        self.stream = stream
        self.stream_len = stream_len

        self._bytes_remaining = self.stream_len

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.stream)

    next = __next__

    def _read(self, size, target):
        """Helper function for proxing reads to the underlying stream.

        Args:
            size (int): Maximum number of bytes to read. Will be
                coerced, if None or -1, to the number of remaining bytes
                in the stream. Will likewise be coerced if greater than
                the number of remaining bytes, to avoid making a
                blocking call to the wrapped stream.
            target (callable): Once `size` has been fixed up, this function
                will be called to actually do the work.

        Returns:
            bytes: Data read from the stream, as returned by `target`.

        """

        # NOTE(kgriffs): Default to reading all remaining bytes if the
        # size is not specified or is out of bounds. This behaves
        # similarly to the IO streams passed in by non-wsgiref servers.
        if (size is None or size == -1 or size > self._bytes_remaining):
            size = self._bytes_remaining

        self._bytes_remaining -= size
        return target(size)

    def readable(self):
        """Always returns ``True``."""
        return True

    def seekable(self):
        """Always returns ``False``."""
        return False

    def writeable(self):
        """Always returns ``False``."""
        return False

    def read(self, size=None):
        """Read from the stream.

        Args:
            size (int): Maximum number of bytes/characters to read.
                Defaults to reading until EOF.

        Returns:
            bytes: Data read from the stream.

        """

        return self._read(size, self.stream.read)

    def readline(self, limit=None):
        """Read a line from the stream.

        Args:
            limit (int): Maximum number of bytes/characters to read.
                Defaults to reading until EOF.

        Returns:
            bytes: Data read from the stream.

        """

        return self._read(limit, self.stream.readline)

    def readlines(self, hint=None):
        """Read lines from the stream.

        Args:
            hint (int): Maximum number of bytes/characters to read.
                Defaults to reading until EOF.

        Returns:
            bytes: Data read from the stream.

        """

        return self._read(hint, self.stream.readlines)

    def write(self, data):
        """Always raises IOError; writing is not supported."""

        raise IOError('Stream is not writeable')

    def exhaust(self, chunk_size=64 * 1024):
        """Exhaust the stream.

        This consumes all the data left until the limit is reached.

        Args:
            chunk_size (int): The size for a chunk (default: 64 KB).
                It will read the chunk until the stream is exhausted.
        """
        while True:
            chunk = self.read(chunk_size)
            if not chunk:
                break

    @property
    def is_exhausted(self):
        """If the stream is exhausted this attribute is ``True``."""
        return self._bytes_remaining <= 0


# NOTE(kgriffs): Alias for backwards-compat
Body = BoundedStream
