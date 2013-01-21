"""Defines the Response class

Copyright 2013 by Rackspace Hosting, Inc.

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

DEFAULT_CONTENT_TYPE = 'application/json; charset=utf-8'
CONTENT_TYPE_NAMES = set(['Content-Type', 'content-type', 'CONTENT-TYPE'])


class Response(object):
    """Represents an HTTP response to a client request"""

    __slots__ = ('status', '_headers', 'body', 'stream', 'stream_len')

    def __init__(self):
        """Initialize response attributes to default values

        Args:
            wsgierrors: File-like stream for logging errors

        """

        self.status = '200 OK'
        self._headers = []

        self.body = None
        self.stream = None
        self.stream_len = None

    def set_header(self, name, value):
        """Set a header for this response to a given value.

        Warning: Overwrites the existing value, if any.

        Args:
            name: Header name to set. Must be of type str or StringType, and
                only character values 0x00 through 0xFF may be used on
                platforms that use wide characters.
            value: Value for the header. Must be of type str or StringType, and
                only character values 0x00 through 0xFF may be used on
                platforms that use wide characters.

        """

        self._headers.append((name, value))

    def set_headers(self, headers):
        """Set several headers at once. May be faster than set_header().

        Warning: Overwrites existing values, if any.

        Args:
            headers: A dict containing header names and values to set. Both
                names and values must be of type str or StringType, and
                only character values 0x00 through 0xFF may be used on
                platforms that use wide characters.

        Raises:
            ValueError: headers was not a dictionary or list of tuples.

        """

        self._headers.extend(headers.items())

    def _wsgi_headers(self):
        """Convert headers into the format expected by WSGI servers"""

        if (self.body is not None) or (self.stream is not None):
            headers = self._headers
            for name, value in headers:
                if name in CONTENT_TYPE_NAMES:
                    break
            else:
                self._headers.append(('Content-Type', DEFAULT_CONTENT_TYPE))

        return self._headers
