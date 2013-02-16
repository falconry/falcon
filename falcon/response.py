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

import falcon


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
        last_modified: A datetime (UTC) instance to use as the Last-Modified
            header. Falcon will format the datetime as an HTTP date. See
            also: http://goo.gl/R7So4
        retry_after: Number of seconds to use as the value for the Retry-After
            header. Note that the HTTP-date option is not supported. See
            also: http://goo.gl/DIrWr
        vary: Value to use for the Vary header. From Wikipedia: "Tells
            downstream proxies how to match future request headers to decide
            whether the cached response can be used rather than requesting a
            fresh one from the origin server." See also: http://goo.gl/NGHdL

            Assumed to be an array of values. For a single asterisk or field
            value, simply pass a single-element array.
        location: Value for the Location header. Note that relative URIs are
            OK per http://goo.gl/DbVqR
        content_location: Value for the Content-Location header. See
            also: http://goo.gl/1slsA
        content_range: A tuple to use in constructing a value for the
            Content-Range header. The tuple has the form (start, end, length),
            where start and end is the inclusive byte range, and length is the
            total number of bytes, or '*' if unknown.

            Note: You only need to use the alternate form, "bytes */1234", for
            responses that use the status "416 Range Not Satisfiable". In this
            case, raising falcon.HTTPRangeNotSatisfiable will do the right
            thing.

            See also: http://goo.gl/Iglhp


    """

    __slots__ = (
        'body',
        'cache_control',
        'content_location',
        'content_range',
        'content_type',
        'data',
        'etag',
        '_headers',
        'last_modified',
        'location',
        'retry_after',
        'status',
        'stream',
        'stream_len',
        'vary'
    )

    def __init__(self):
        """Initialize response attributes to default values

        Args:
            wsgierrors: File-like stream for logging errors

        """

        self.status = '200 OK'
        self._headers = {}

        self.body = None
        self.data = None
        self.stream = None
        self.stream_len = None

        self.content_type = None
        self.etag = None
        self.cache_control = None
        self.last_modified = None
        self.retry_after = None
        self.vary = None
        self.location = None
        self.content_location = None
        self.content_range = None

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

        self._headers[name] = value

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

        self._headers.update(headers)

    def _append_attribute_headers(self, headers):  # NOQA
        if self.etag is not None:
            headers['ETag'] = self.etag

        if self.cache_control is not None:
            headers['Cache-Control'] = ', '.join(self.cache_control)

        if self.last_modified is not None:
            headers['Last-Modified'] = falcon.dt_to_http(self.last_modified)

        if self.retry_after is not None:
            headers['Retry-After'] = str(self.retry_after)

        if self.vary is not None:
            headers['Vary'] = ', '.join(self.vary)

        if self.location is not None:
            headers['Location'] = self.location

        if self.content_location is not None:
            headers['Content-Location'] = self.content_location

        content_range = self.content_range
        if content_range is not None:
            # PERF: Concatenation is faster than % string formatting as well
            #       as ''.join() in this case.
            formatted_range = ('bytes ' +
                               str(content_range[0]) + '-' +
                               str(content_range[1]) + '/' +
                               str(content_range[2]))

            headers['Content-Range'] = formatted_range

    def _wsgi_headers(self, media_type=None):
        """Convert headers into the format expected by WSGI servers

        Args:
            media_type: Default media type to use for the Content-Type
                header if the header was not set explicitly. (default None)

        """

        headers = self._headers

        if self.content_type is not None:
            headers['Content-Type'] = self.content_type

        self._append_attribute_headers(headers)

        set_content_type = (media_type is not None and
                            'Content-Type' not in headers and
                            'content-type' not in headers)

        if set_content_type:
            headers['Content-Type'] = media_type

        return list(headers.items())
