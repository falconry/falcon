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

import six

from falcon.response_helpers import header_property, format_range
from falcon.util import dt_to_http, uri


class Response(object):
    """Represents an HTTP response to a client request.

    Note:
        `Response` is not meant to be instantiated directly by responders.

    Attributes:
        status (str): HTTP status line, such as "200 OK"

            Note:
                Falcon provides a number of constants for common status
                codes. They all start with the ``HTTP_`` prefix, as in:
                ``falcon.HTTP_204``.

        body (str or unicode): String representing response content. If
            Unicode, Falcon will encode as UTF-8 in the response. If
            data is already a byte string, use the data attribute
            instead (it's faster).
        body_encoded (bytes): Returns a UTF-8 encoded version of `body`.
        data (bytes): Byte string representing response content.

            Note:
                Under Python 2.x, if your content is of type *str*, setting
                efficient. However, if your text is of type *unicode*,
                you will want to use the *body* attribute instead.

                Under Python 3.x, the 2.x *str* type can be thought of as
                having been replaced with what was once the *unicode* type,
                and so you will want to use the `body` attribute to
                ensure Unicode characters are properly encoded in the
                response body.

        stream: Either a file-like object with a *read()* method that takes
            an optional size argument and returns a block of bytes, or an
            iterable object, representing response content, and yielding
            blocks as byte strings. Falcon will use wsgi.file_wrapper, if
            provided by the WSGI server, in order to efficiently serve
            file-like objects.

        stream_len (int): Expected length of *stream* (e.g., file size).
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
        self.status = '200 OK'
        self._headers = {}

        self._body = None
        self._body_encoded = None
        self.data = None
        self.stream = None
        self.stream_len = None

    def _get_body(self):
        return self._body

    def _set_body(self, value):
        self._body = value
        self._body_encoded = None

    # NOTE(flaper87): Lets use a property
    # for the body in case its content was
    # encoded and then modified.
    body = property(_get_body, _set_body)

    @property
    def body_encoded(self):
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

        Warning:
            Calling this method overwrites the existing value, if any.

        Args:
            name (str): Header name to set (case-insensitive). Must be of
                type str or StringType, and only character values 0x00
                through 0xFF may be used on platforms that use wide
                characters.
            value (str): Value for the header. Must be of type str or
                StringType, and only character values 0x00 through 0xFF
                may be used on platforms that use wide characters.

        """

        # NOTE(kgriffs): normalize name by lowercasing it
        self._headers[name.lower()] = value

    def set_headers(self, headers):
        """Set several headers at once.

        Warning:
            Calling this method overwrites existing values, if any.

        Args:
            headers (dict or list): A dictionary of header names and values
                to set, or list of (name, value) tuples. Both names and
                values must be of type
                str or StringType, and only character values 0x00 through
                0xFF may be used on platforms that use wide characters.

                Note:
                    Falcon can process a list of tuples slightly faster
                    than a dict.

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

        The tuple has the form ``(start, end, length)``, where *start* and
        *end* designate the byte range (inclusive), and *length* is the
        total number of bytes, or '*' if unknown. You may use *int*'s for
        these numbers (no need to convert to a *str* first).

        Note:
            You only need to use the alternate form, "bytes */1234", for
            responses that use the status "416 Range Not Satisfiable". In this
            case, raising falcon.HTTPRangeNotSatisfiable will do the right
            thing.

            See also: http://goo.gl/Iglhp
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

        Note:
            Falcon will format the datetime as an HTTP date.
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

        Set this property to an iterable of header names. For a single
        asterisk or field value, simply pass a single-element list or
        tuple.

        "Tells downstream proxies how to match future request headers
        to decide whether the cached response can be used rather than
        requesting a fresh one from the origin server."

        (Wikipedia)

        See also: http://goo.gl/NGHdL

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
