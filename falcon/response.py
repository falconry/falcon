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

from six import PY2
from six import text_type as TEXT_TYPE
from six import string_types as STRING_TYPES
from six.moves.http_cookies import SimpleCookie, CookieError

from falcon.response_helpers import header_property, format_range
from falcon.response_helpers import is_ascii_encodable
from falcon.util import dt_to_http, TimezoneGMT
from falcon.util.uri import encode as uri_encode
from falcon.util.uri import encode_value as uri_encode_value

GMT_TIMEZONE = TimezoneGMT()


class Response(object):
    """Represents an HTTP response to a client request.

    Note:
        `Response` is not meant to be instantiated directly by responders.

    Attributes:
        status (str): HTTP status line (e.g., '200 OK'). Falcon requires the
            full status line, not just the code (e.g., 200). This design
            makes the framework more efficient because it does not have to
            do any kind of conversion or lookup when composing the WSGI
            response.

            If not set explicitly, the status defaults to '200 OK'.

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

            Use this attribute in lieu of `body` when your content is
            already a byte string (``str`` or ``bytes`` in Python 2, or
            simply ``bytes`` in Python 3). See also the note below.

            Note:
                Under Python 2.x, if your content is of type ``str``, using
                the `data` attribute instead of `body` is the most
                efficient approach. However, if
                your text is of type ``unicode``, you will need to use the
                `body` attribute instead.

                Under Python 3.x, on the other hand, the 2.x ``str`` type can
                be thought of as
                having been replaced by what was once the ``unicode`` type,
                and so you will need to always use the `body` attribute for
                strings to
                ensure Unicode characters are properly encoded in the
                HTTP response.

        stream: Either a file-like object with a `read()` method that takes
            an optional size argument and returns a block of bytes, or an
            iterable object, representing response content, and yielding
            blocks as byte strings. Falcon will use *wsgi.file_wrapper*, if
            provided by the WSGI server, in order to efficiently serve
            file-like objects.

        stream_len (int): Expected length of `stream` (e.g., file size).
    """

    __slots__ = (
        '_body',  # Stuff
        '_body_encoded',  # Stuff
        'data',
        '_headers',
        '_cookies',
        'status',
        'stream',
        'stream_len'
    )

    def __init__(self):
        self.status = '200 OK'
        self._headers = {}

        # NOTE(tbug): will be set to a SimpleCookie object
        # when cookie is set via set_cookie
        self._cookies = None

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
            if isinstance(body, TEXT_TYPE):
                self._body_encoded = body.encode('utf-8')

        return self._body_encoded

    def set_stream(self, stream, stream_len):
        """Convenience method for setting both `stream` and `stream_len`.

        Although the `stream` and `stream_len` properties may be set
        directly, using this method ensures `stream_len` is not
        accidentally neglected.

        """

        self.stream = stream
        self.stream_len = stream_len

    def set_cookie(self, name, value, expires=None, max_age=None,
                   domain=None, path=None, secure=True, http_only=True):
        """Set a response cookie.

        Note:
            This method can be called multiple times to add one or
            more cookies to the response.

        See Also:
            To learn more about setting cookies, see
            :ref:`Setting Cookies <setting-cookies>`. The parameters listed
            below correspond to those defined in `RFC 6265`_.

        Args:
            name (str):
                Cookie name
            value (str):
                Cookie value
            expires (datetime): Specifies when the cookie should expire. By
                default, cookies expire when the user agent exits.
            max_age (int): Defines the lifetime of the cookie in seconds.
                After the specified number of seconds elapse, the client
                should discard the cookie.
            domain (str): Specifies the domain for which the cookie is valid.
                An explicitly specified domain must always start with a dot.
                A value of 0 means the cookie should be discarded immediately.
            path (str): Specifies the subset of URLs to
                which this cookie applies.
            secure (bool): Direct the client to use only secure means to
                contact the origin server whenever it sends back this cookie
                (default: ``True``). Warning: You will also need to enforce
                HTTPS for the cookies to be transfered securely.
            http_only (bool): Direct the client to only transfer the cookie
                with unscripted HTTP requests (default: ``True``). This is
                intended to mitigate some forms of cross-site scripting.

        Raises:
            KeyError: `name` is not a valid cookie name.
            ValueError: `value` is not a valid cookie value.

        .. _RFC 6265:
            http://tools.ietf.org/html/rfc6265

        """

        if not is_ascii_encodable(name):
            raise KeyError('"name" is not ascii encodable')
        if not is_ascii_encodable(value):
            raise ValueError('"value" is not ascii encodable')

        if PY2:  # pragma: no cover
            name = str(name)
            value = str(value)

        if self._cookies is None:
            self._cookies = SimpleCookie()

        try:
            self._cookies[name] = value
        except CookieError as e:  # pragma: no cover
            # NOTE(tbug): we raise a KeyError here, to avoid leaking
            # the CookieError to the user. SimpleCookie (well, BaseCookie)
            # only throws CookieError on issues with the cookie key
            raise KeyError(str(e))

        if expires:
            # set Expires on cookie. Format is Wdy, DD Mon YYYY HH:MM:SS GMT

            # NOTE(tbug): we never actually need to
            # know that GMT is named GMT when formatting cookies.
            # It is a function call less to just write "GMT" in the fmt string:
            fmt = "%a, %d %b %Y %H:%M:%S GMT"
            if expires.tzinfo is None:
                # naive
                self._cookies[name]["expires"] = expires.strftime(fmt)
            else:
                # aware
                gmt_expires = expires.astimezone(GMT_TIMEZONE)
                self._cookies[name]["expires"] = gmt_expires.strftime(fmt)

        if max_age:
            self._cookies[name]["max-age"] = max_age

        if domain:
            self._cookies[name]["domain"] = domain

        if path:
            self._cookies[name]["path"] = path

        if secure:
            self._cookies[name]["secure"] = secure

        if http_only:
            self._cookies[name]["httponly"] = http_only

    def unset_cookie(self, name):
        """Unset a cookie from the response
        """
        if self._cookies is not None and name in self._cookies:
            del self._cookies[name]

    def set_header(self, name, value):
        """Set a header for this response to a given value.

        Warning:
            Calling this method overwrites the existing value, if any.

        Warning:
            For setting cookies, see instead :meth:`~.set_cookie`

        Args:
            name (str): Header name to set (case-insensitive). Must be of
                type ``str`` or ``StringType``, and only character values 0x00
                through 0xFF may be used on platforms that use wide
                characters.
            value (str): Value for the header. Must be of type ``str`` or
                ``StringType``, and only character values 0x00 through 0xFF
                may be used on platforms that use wide characters.

        """

        # NOTE(kgriffs): normalize name by lowercasing it
        self._headers[name.lower()] = value

    def append_header(self, name, value):
        """Set or append a header for this response.

        Warning:
            If the header already exists, the new value will be appended
            to it, delimited by a comma. Most header specifications support
            this format, Cookie and Set-Cookie being the notable exceptions.

        Warning:
            For setting cookies, see :py:meth:`~.set_cookie`

        Args:
            name (str): Header name to set (case-insensitive). Must be of
                type ``str`` or ``StringType``, and only character values 0x00
                through 0xFF may be used on platforms that use wide
                characters.
            value (str): Value for the header. Must be of type ``str`` or
                ``StringType``, and only character values 0x00 through 0xFF
                may be used on platforms that use wide characters.

        """
        name = name.lower()
        if name in self._headers:
            value = self._headers[name] + ',' + value

        self._headers[name] = value

    def set_headers(self, headers):
        """Set several headers at once.

        Warning:
            Calling this method overwrites existing values, if any.

        Args:
            headers (dict or list): A dictionary of header names and values
                to set, or ``list`` of (*name*, *value*) tuples. Both *name*
                and *value* must be of type ``str`` or ``StringType``, and
                only character values 0x00 through 0xFF may be used on
                platforms that use wide characters.

                Note:
                    Falcon can process a list of tuples slightly faster
                    than a dict.

        Raises:
            ValueError: `headers` was not a ``dict`` or ``list`` of ``tuple``.

        """

        if isinstance(headers, dict):
            headers = headers.items()

        # NOTE(kgriffs): We can't use dict.update because we have to
        # normalize the header names.
        _headers = self._headers
        for name, value in headers:
            _headers[name.lower()] = value

    def add_link(self, target, rel, title=None, title_star=None,
                 anchor=None, hreflang=None, type_hint=None):
        """
        Add a link header to the response.

        See also: https://tools.ietf.org/html/rfc5988

        Note:
            Calling this method repeatedly will cause each link to be
            appended to the Link header value, separated by commas.

        Note:
            So-called "link-extension" elements, as defined by RFC 5988,
            are not yet supported. See also Issue #288.

        Args:
            target (str): Target IRI for the resource identified by the
                link. Will be converted to a URI, if necessary, per
                RFC 3987, Section 3.1.
            rel (str): Relation type of the link, such as "next" or
                "bookmark". See also http://goo.gl/618GHr for a list
                of registered link relation types.

        Kwargs:
            title (str): Human-readable label for the destination of
                the link (default ``None``). If the title includes non-ASCII
                characters, you will need to use `title_star` instead, or
                provide both a US-ASCII version using `title` and a
                Unicode version using `title_star`.
            title_star (tuple of str): Localized title describing the
                destination of the link (default ``None``). The value must be a
                two-member tuple in the form of (*language-tag*, *text*),
                where *language-tag* is a standard language identifier as
                defined in RFC 5646, Section 2.1, and *text* is a Unicode
                string.

                Note:
                    *language-tag* may be an empty string, in which case the
                    client will assume the language from the general context
                    of the current request.

                Note:
                    *text* will always be encoded as UTF-8. If the string
                    contains non-ASCII characters, it should be passed as
                    a ``unicode`` type string (requires the 'u' prefix in
                    Python 2).

            anchor (str): Override the context IRI with a different URI
                (default None). By default, the context IRI for the link is
                simply the IRI of the requested resource. The value
                provided may be a relative URI.
            hreflang (str or iterable): Either a single *language-tag*, or
                a ``list`` or ``tuple`` of such tags to provide a hint to the
                client as to the language of the result of following the link.
                A list of tags may be given in order to indicate to the
                client that the target resource is available in multiple
                languages.
            type_hint(str): Provides a hint as to the media type of the
                result of dereferencing the link (default ``None``). As noted
                in RFC 5988, this is only a hint and does not override the
                Content-Type header returned when the link is followed.

        """

        # PERF(kgriffs): Heuristic to detect possiblity of an extension
        # relation type, in which case it will be a URL that may contain
        # reserved characters. Otherwise, don't waste time running the
        # string through uri.encode
        #
        # Example values for rel:
        #
        #     "next"
        #     "http://example.com/ext-type"
        #     "https://example.com/ext-type"
        #     "alternate http://example.com/ext-type"
        #     "http://example.com/ext-type alternate"
        #
        if '//' in rel:
            if ' ' in rel:
                rel = ('"' +
                       ' '.join([uri_encode(r) for r in rel.split()]) +
                       '"')
            else:
                rel = '"' + uri_encode(rel) + '"'

        value = '<' + uri_encode(target) + '>; rel=' + rel

        if title is not None:
            value += '; title="' + title + '"'

        if title_star is not None:
            value += ("; title*=UTF-8'" + title_star[0] + "'" +
                      uri_encode_value(title_star[1]))

        if type_hint is not None:
            value += '; type="' + type_hint + '"'

        if hreflang is not None:
            if isinstance(hreflang, STRING_TYPES):
                value += '; hreflang=' + hreflang
            else:
                value += '; '
                value += '; '.join(['hreflang=' + lang for lang in hreflang])

        if anchor is not None:
            value += '; anchor="' + uri_encode(anchor) + '"'

        _headers = self._headers
        if 'link' in _headers:
            _headers['link'] += ', ' + value
        else:
            _headers['link'] = value

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
        uri_encode)

    content_range = header_property(
        'Content-Range',
        """A tuple to use in constructing a value for the Content-Range header.

        The tuple has the form (*start*, *end*, *length*), where *start* and
        *end* designate the byte range (inclusive), and *length* is the
        total number of bytes, or '\*' if unknown. You may pass ``int``'s for
        these numbers (no need to convert to ``str`` beforehand).

        Note:
            You only need to use the alternate form, 'bytes \*/1234', for
            responses that use the status '416 Range Not Satisfiable'. In this
            case, raising ``falcon.HTTPRangeNotSatisfiable`` will do the right
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
        """Sets the Last-Modified header. Set to a ``datetime`` (UTC) instance.

        Note:
            Falcon will format the ``datetime`` as an HTTP date string.
        """,
        dt_to_http)

    location = header_property(
        'Location',
        'Sets the Location header.',
        uri_encode)

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
        asterisk or field value, simply pass a single-element ``list`` or
        ``tuple``.

        "Tells downstream proxies how to match future request headers
        to decide whether the cached response can be used rather than
        requesting a fresh one from the origin server."

        (Wikipedia)

        See also: http://goo.gl/NGHdL

        """,
        lambda v: ', '.join(v))

    def _wsgi_headers(self, media_type=None, py2=PY2):
        """Convert headers into the format expected by WSGI servers.

        Args:
            media_type: Default media type to use for the Content-Type
                header if the header was not set explicitly (default ``None``).

        """

        headers = self._headers

        # PERF(kgriffs): Using "in" like this is faster than using
        # dict.setdefault (tested on py27).
        set_content_type = (media_type is not None and
                            'content-type' not in headers)

        if set_content_type:
            headers['content-type'] = media_type

        if py2:  # pragma: no cover
            # PERF(kgriffs): Don't create an extra list object if
            # it isn't needed.
            items = headers.items()
        else:
            items = list(headers.items())  # pragma: no cover

        if self._cookies is not None:
            # PERF(tbug):
            # The below implementation is ~23% faster than
            # the alternative:
            #
            #     self._cookies.output().split("\\r\\n")
            #
            # Even without the .split("\\r\\n"), the below
            # is still ~17% faster, so don't use .output()
            items += [("set-cookie", c.OutputString())
                      for c in self._cookies.values()]
        return items
