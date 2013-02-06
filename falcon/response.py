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

CONTENT_TYPE_NAMES = set(['Content-Type', 'content-type', 'CONTENT-TYPE'])


class Response(object):
    """Represents an HTTP response to a client request


    Attributes:
        status: HTTP status code, such as "200 OK" (see also falcon.HTTP_*)
        body: String representing response content. If Unicode, Falcon will
            encode as UTF-8 in the response. If data is already a byte string,
            use the data attribute instead (it's faster).
        data: Byte string representing response content.
        stream: Iterable stream-like object, representing response content.
        stream_len: Expected length of stream (e.g., file size).
        content_type: Value for the Content-Type header
        etag: Value for the ETag header
        cache_control: An array of cache directives (see http://goo.gl/fILS5
            and http://goo.gl/sM9Xx for a good description.) The array will be
            joined with ', ' to produce the value for the Cache-Control
            header.


    """

    __slots__ = (
        'body',
        'cache_control',
        'content_type',
        'data',
        'etag',
        '_headers',
        'status',
        'stream',
        'stream_len'
    )

    def __init__(self, default_media_type):
        """Initialize response attributes to default values

        Args:
            wsgierrors: File-like stream for logging errors

        """

        self.status = '200 OK'
        self._headers = [('Content-Type', default_media_type)]

        self.body = None
        self.data = None
        self.stream = None
        self.stream_len = None

        self.content_type = None
        self.etag = None
        self.cache_control = None

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

    def _wsgi_headers(self, set_content_type):
        """Convert headers into the format expected by WSGI servers

        WARNING: Only call once! Not idempotent.

        """

        headers = self._headers

        if not set_content_type:
            del headers[0]
        elif self.content_type is not None:
            headers.append(('Content-Type', self.content_type))

        if self.etag is not None:
            headers.append(('ETag', self.etag))

        if self.cache_control is not None:
            headers.append(('Cache-Control', ', '.join(self.cache_control)))

        return headers
