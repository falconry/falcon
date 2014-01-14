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

import six

from falcon.response_helpers import header_property, format_range
from falcon.util import dt_to_http, uri


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
    """

    __slots__ = (
        '_body',  # Stuff
        '_body_encoded',  # Stuff
        'data',
        '_headers',
        'status',
        'stream',
        'stream_len'
    )

    def __init__(self):
        """Initialize response attributes to default values

        Args:
            wsgierrors: File-like stream for logging errors

        """

        self.status = '200 OK'
        self._headers = {}

        self._body = None
        self._body_encoded = None
        self.data = None
        self.stream = None
        self.stream_len = None

    def _get_body(self):
        """Returns the body as-is."""
        return self._body

    def _set_body(self, value):
        """Sets the body and clears the encoded cache."""
        self._body = value
        self._body_encoded = None

    # NOTE(flaper87): Lets use a property
    # for the body in case its content was
    # encoded and then modified.
    body = property(_get_body, _set_body)

    @property
    def body_encoded(self):
        """Encode the body and return it

        This property will encode `_body` and
        cache the result in the `_body_encoded`
        attribute.
        """
        # NOTE(flaper87): Notice this property
        # is not thread-safe. If body is modified
        # before this property returns, we might
        # end up returning None.
        body = self._body
        if body and self._body_encoded is None:

            # NOTE(flaper87): Assume it is an
            # encoded str, then check and encode
            # if it isn't.
            self._body_encoded = body
            if isinstance(body, six.text_type):
                self._body_encoded = body.encode('utf-8')

        return self._body_encoded

    def set_header(self, name, value):
        """Set a header for this response to a given value.

        Warning: Overwrites the existing value, if any.

        Args:
            name: Header name to set (case-insensitive). Must be of type str
                or StringType, and only character values 0x00 through 0xFF
                may be used on platforms that use wide characters.
            value: Value for the header. Must be of type str or StringType, and
                only character values 0x00 through 0xFF may be used on
                platforms that use wide characters.

        """

        # NOTE(kgriffs): normalize name by lowercasing it
        self._headers[name.lower()] = value

    def set_headers(self, headers):
        """Set several headers at once.

        Warning: Overwrites existing values, if any.

        Args:
            headers: A dict containing header names and values to set, or
                list of (name, value) tuples. A list can be read slightly
                faster than a dict. Both names and values must be of type
                str or StringType, and only character values 0x00 through
                0xFF may be used on platforms that use wide characters.

        Raises:
            ValueError: headers was not a dictionary or list of tuples.

        """

        if isinstance(headers, dict):
            headers = headers.items()

        # NOTE(kgriffs): We can't use dict.update because we have to
        # normalize the header names.
        _headers = self._headers
        for name, value in headers:
            _headers[name.lower()] = value

    cache_control = header_property(
        'Cache-Control',
        """Sets the Cache-Control header.

        Used to set a list of cache directives to use as the value of the
        Cache-Control header. The list will be joined with ", " to produce
        the value for the header.
        """,
        lambda v: ', '.join(v))

    content_location = header_property(
        'Content-Location',
        'Sets the Content-Location header.',
        uri.encode)

    content_range = header_property(
        'Content-Range',
        """A tuple to use in constructing a value for the Content-Range header.

        The tuple has the form (start, end, length), where start and end is
        the inclusive byte range, and length is the total number of bytes, or
        '*' if unknown.

        Note: You only need to use the alternate form, "bytes */1234", for
        responses that use the status "416 Range Not Satisfiable". In this
        case, raising falcon.HTTPRangeNotSatisfiable will do the right
        thing.

        See also: http://goo.gl/Iglhp)
        """,
        format_range)

    content_type = header_property(
        'Content-Type',
        'Sets the Content-Type header.')

    etag = header_property(
        'ETag',
        'Sets the ETag header.')

    last_modified = header_property(
        'Last-Modified',
        """Sets the Last-Modified header. Set to a datetime (UTC) instance.

        Note: Falcon will format the datetime as an HTTP date.
        """,
        dt_to_http)

    location = header_property(
        'Location',
        'Sets the Location header.',
        uri.encode)

    retry_after = header_property(
        'Retry-After',
        """Sets the Retry-After header.

        The expected value is an integral number of seconds to use as the
        value for the header. The HTTP-date syntax is not supported.
        """,
        str)

    vary = header_property(
        'Vary',
        """Value to use for the Vary header.

        From Wikipedia:

            "Tells downstream proxies how to match future request headers
            to decide whether the cached response can be used rather than
            requesting a fresh one from the origin server."

            See also: http://goo.gl/NGHdL

         Set this property to an iterable of header names. For a single
         asterisk or field value, simply pass a single-element list or
         tuple.
         """,
        lambda v: ', '.join(v))

    def _wsgi_headers(self, media_type=None):
        """Convert headers into the format expected by WSGI servers.

        Args:
            media_type: Default media type to use for the Content-Type
                header if the header was not set explicitly (default None).

        """

        headers = self._headers

        # PERF(kgriffs): Using "in" like this is faster than using
        # dict.setdefault (tested on py27).
        set_content_type = (media_type is not None and
                            'content-type' not in headers)

        if set_content_type:
            headers['content-type'] = media_type

        if six.PY2:  # pragma: no cover
            # PERF(kgriffs): Don't create an extra list object if
            # it isn't needed.
            return headers.items()

        return list(headers.items())  # pragma: no cover
