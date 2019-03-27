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

"""Response class."""

import mimetypes


from falcon import DEFAULT_MEDIA_TYPE
from falcon.errors import HeaderNotSupported
from falcon.media import Handlers
from falcon.response_helpers import (
    format_content_disposition,
    format_etag_header,
    format_header_value_list,
    format_range,
    header_property,
    is_ascii_encodable,
)
from falcon.util import compat, dt_to_http, structures, TimezoneGMT
from falcon.util.uri import encode as uri_encode
from falcon.util.uri import encode_value as uri_encode_value


SimpleCookie = compat.http_cookies.SimpleCookie
CookieError = compat.http_cookies.CookieError

GMT_TIMEZONE = TimezoneGMT()

# TODO(kgriffs): Uncomment when 3.0 development opens
# _STREAM_LEN_REMOVED_MSG = (
#     'The deprecated stream_len property was removed in Falcon 3.0. '
#     'Please use Response.set_stream() or Response.content_length instead.'
# )


class Response(object):
    """Represents an HTTP response to a client request.

    Note:
        `Response` is not meant to be instantiated directly by responders.

    Keyword Arguments:
        options (dict): Set of global options passed from the API handler.

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

        media (object): A serializable object supported by the media handlers
            configured via :class:`falcon.RequestOptions`.

            See :ref:`media` for more information regarding media handling.

        body (str or unicode): String representing response content.

            If set to a Unicode type (``unicode`` in Python 2, or
            ``str`` in Python 3), Falcon will encode the text as UTF-8
            in the response. If the content is already a byte string,
            use the :attr:`data` attribute instead (it's faster).

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

            Note:
                If the stream is set to an iterable object that requires
                resource cleanup, it can implement a close() method to do so.
                The close() method will be called upon completion of the request.

        stream_len (int): Deprecated alias for :attr:`content_length`.

        context (dict): Dictionary to hold any data about the response which is
            specific to your app. Falcon itself will not interact with this
            attribute after it has been initialized.

        context (object): Empty object to hold any data (in its attributes)
            about the response which is specific to your app (e.g. session
            object). Falcon itself will not interact with this attribute after
            it has been initialized.

            Note:
                **New in 2.0:** the default `context_type` (see below) was
                changed from dict to a bare class, and the preferred way to
                pass response-specific data is now to set attributes directly
                on the `context` object, for example::

                    resp.context.cache_strategy = 'lru'

        context_type (class): Class variable that determines the factory or
            type to use for initializing the `context` attribute. By default,
            the framework will instantiate bare objects (instances of the bare
            :class:`falcon.Context` class). However, you may override this
            behavior by creating a custom child class of ``falcon.Response``,
            and then passing that new class to `falcon.API()` by way of the
            latter's `response_type` parameter.

            Note:
                When overriding `context_type` with a factory function (as
                opposed to a class), the function is called like a method of
                the current Response instance. Therefore the first argument is
                the Response instance itself (self).

        options (dict): Set of global options passed from the API handler.

        headers (dict): Copy of all headers set for the response,
            sans cookies. Note that a new copy is created and returned each
            time this property is referenced.

        complete (bool): Set to ``True`` from within a middleware method to
            signal to the framework that request processing should be
            short-circuited (see also :ref:`Middleware <middleware>`).
    """

    __slots__ = (
        'body',
        'context',
        'options',
        'status',
        'stream',
        '_cookies',
        '_data',
        '_extra_headers',
        '_headers',
        '_media',
        '__dict__',
    )

    complete = False

    # Child classes may override this
    context_type = structures.Context

    def __init__(self, options=None):
        self.status = '200 OK'
        self._headers = {}

        # NOTE(kgriffs): Collection of additional headers as a list of raw
        #   tuples, to use in cases where we need more control over setting
        #   headers and duplicates are allowable or even necessary.
        #
        # PERF(kgriffs): Save some CPU cycles and a few bytes of RAM by
        #   only instantiating the list object later on IFF it is needed.
        self._extra_headers = None

        self.options = options if options else ResponseOptions()

        # NOTE(tbug): will be set to a SimpleCookie object
        # when cookie is set via set_cookie
        self._cookies = None

        self.body = None
        self.stream = None
        self._data = None
        self._media = None

        self.context = self.context_type()

    @property
    def data(self):
        # NOTE(kgriffs): Test explicitly against None since the
        # app may have set it to an empty binary string.
        if self._data is not None:
            return self._data

        # NOTE(kgriffs): Test explicitly against None since the
        # app may have set it to an empty string that should still
        # be serialized.
        if self._media is None:
            return None

        if not self.content_type:
            self.content_type = self.options.default_media_type

        handler = self.options.media_handlers.find_by_media_type(
            self.content_type,
            self.options.default_media_type
        )

        # NOTE(kgriffs): Set _data to avoid re-serializing if the
        # data() property is called multiple times.
        self._data = handler.serialize(
            self._media,
            self.content_type
        )
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def headers(self):
        return self._headers.copy()

    @property
    def media(self):
        return self._media

    @media.setter
    def media(self, obj):
        self._media = obj

        # NOTE(kgriffs): This will be set just-in-time by the data() property,
        # rather than serializing immediately. That way, if media() is called
        # multiple times we don't waste time serializing objects that will
        # just be thrown away.
        self._data = None

    # TODO(kgriffs): Uncomment when 3.0 development opens
    # @property
    # def stream_len(self):
    #     # NOTE(kgriffs): Provide some additional information by raising the
    #     #   error explicitly.
    #     raise AttributeError(_STREAM_LEN_REMOVED_MSG)

    # TODO(kgriffs): Uncomment when 3.0 development opens
    # @stream_len.setter
    # def stream_len(self, value):
    #     # NOTE(kgriffs): We explicitly disallow setting the deprecated attribute
    #     #   so that apps relying on it do not fail silently.
    #     raise AttributeError(_STREAM_LEN_REMOVED_MSG)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.status)

    def set_stream(self, stream, content_length):
        """Convenience method for setting both `stream` and `content_length`.

        Although the `stream` and `content_length` properties may be set
        directly, using this method ensures `content_length` is not
        accidentally neglected when the length of the stream is known in
        advance. Using this method is also slightly more performant
        as compared to setting the properties individually.

        Note:
            If the stream length is unknown, you can set `stream`
            directly, and ignore `content_length`. In this case, the
            WSGI server may choose to use chunked encoding or one
            of the other strategies suggested by PEP-3333.

        Args:
            stream: A readable file-like object.
            content_length (int): Length of the stream, used for the
                Content-Length header in the response.
        """

        self.stream = stream

        # PERF(kgriffs): Set directly rather than incur the overhead of
        #   the self.content_length property.
        self._headers['content-length'] = str(content_length)

    def set_cookie(self, name, value, expires=None, max_age=None,
                   domain=None, path=None, secure=None, http_only=True):
        """Set a response cookie.

        Note:
            This method can be called multiple times to add one or
            more cookies to the response.

        See Also:
            To learn more about setting cookies, see
            :ref:`Setting Cookies <setting-cookies>`. The parameters
            listed below correspond to those defined in `RFC 6265`_.

        Args:
            name (str): Cookie name
            value (str): Cookie value

        Keyword Args:
            expires (datetime): Specifies when the cookie should expire.
                By default, cookies expire when the user agent exits.

                (See also: RFC 6265, Section 4.1.2.1)
            max_age (int): Defines the lifetime of the cookie in
                seconds. By default, cookies expire when the user agent
                exits. If both `max_age` and `expires` are set, the
                latter is ignored by the user agent.

                Note:
                    Coercion to ``int`` is attempted if provided with
                    ``float`` or ``str``.

                (See also: RFC 6265, Section 4.1.2.2)

            domain (str): Restricts the cookie to a specific domain and
                any subdomains of that domain. By default, the user
                agent will return the cookie only to the origin server.
                When overriding this default behavior, the specified
                domain must include the origin server. Otherwise, the
                user agent will reject the cookie.

                (See also: RFC 6265, Section 4.1.2.3)

            path (str): Scopes the cookie to the given path plus any
                subdirectories under that path (the "/" character is
                interpreted as a directory separator). If the cookie
                does not specify a path, the user agent defaults to the
                path component of the requested URI.

                Warning:
                    User agent interfaces do not always isolate
                    cookies by path, and so this should not be
                    considered an effective security measure.

                (See also: RFC 6265, Section 4.1.2.4)

            secure (bool): Direct the client to only return the cookie
                in subsequent requests if they are made over HTTPS
                (default: ``True``). This prevents attackers from
                reading sensitive cookie data.

                Note:
                    The default value for this argument is normally
                    ``True``, but can be modified by setting
                    :py:attr:`~.ResponseOptions.secure_cookies_by_default`
                    via :any:`API.resp_options`.

                Warning:
                    For the `secure` cookie attribute to be effective,
                    your application will need to enforce HTTPS.

                (See also: RFC 6265, Section 4.1.2.5)

            http_only (bool): Direct the client to only transfer the
                cookie with unscripted HTTP requests
                (default: ``True``). This is intended to mitigate some
                forms of cross-site scripting.

                (See also: RFC 6265, Section 4.1.2.6)

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
            fmt = '%a, %d %b %Y %H:%M:%S GMT'
            if expires.tzinfo is None:
                # naive
                self._cookies[name]['expires'] = expires.strftime(fmt)
            else:
                # aware
                gmt_expires = expires.astimezone(GMT_TIMEZONE)
                self._cookies[name]['expires'] = gmt_expires.strftime(fmt)

        if max_age:
            # RFC 6265 section 5.2.2 says about the max-age value:
            #   "If the remainder of attribute-value contains a non-DIGIT
            #    character, ignore the cookie-av."
            # That is, RFC-compliant response parsers will ignore the max-age
            # attribute if the value contains a dot, as in floating point
            # numbers. Therefore, attempt to convert the value to an integer.
            self._cookies[name]['max-age'] = int(max_age)

        if domain:
            self._cookies[name]['domain'] = domain

        if path:
            self._cookies[name]['path'] = path

        if secure is None:
            is_secure = self.options.secure_cookies_by_default
        else:
            is_secure = secure

        if is_secure:
            self._cookies[name]['secure'] = True

        if http_only:
            self._cookies[name]['httponly'] = http_only

    def unset_cookie(self, name):
        """Unset a cookie in the response

        Clears the contents of the cookie, and instructs the user
        agent to immediately expire its own copy of the cookie.

        Warning:
            In order to successfully remove a cookie, both the
            path and the domain must match the values that were
            used when the cookie was created.
        """
        if self._cookies is None:
            self._cookies = SimpleCookie()

        self._cookies[name] = ''

        # NOTE(Freezerburn): SimpleCookie apparently special cases the
        # expires attribute to automatically use strftime and set the
        # time as a delta from the current time. We use -1 here to
        # basically tell the browser to immediately expire the cookie,
        # thus removing it from future request objects.
        self._cookies[name]['expires'] = -1

    def get_header(self, name, default=None):
        """Retrieve the raw string value for the given header.

        Normally, when a header has multiple values, they will be
        returned as a single, comma-delimited string. However, the
        Set-Cookie header does not support this format, and so
        attempting to retrieve it will raise an error.

        Args:
            name (str): Header name, case-insensitive. Must be of type ``str``
                or ``StringType``, and only character values 0x00 through 0xFF
                may be used on platforms that use wide characters.
        Keyword Args:
            default: Value to return if the header
                is not found (default ``None``).

        Raises:
            ValueError: The value of the 'Set-Cookie' header(s) was requested.

        Returns:
            str: The value of the specified header if set, or
            the default value if not set.
        """

        # NOTE(kgriffs): normalize name by lowercasing it
        name = name.lower()

        if name == 'set-cookie':
            raise HeaderNotSupported('Getting Set-Cookie is not currently supported.')

        return self._headers.get(name, default)

    def set_header(self, name, value):
        """Set a header for this response to a given value.

        Warning:
            Calling this method overwrites any values already set for this
            header. To append an additional value for this header, use
            :meth:`~.append_header` instead.

        Warning:
            This method cannot be used to set cookies; instead, use
            :meth:`~.append_header` or :meth:`~.set_cookie`.

        Args:
            name (str): Header name (case-insensitive). The restrictions
                noted below for the header's value also apply here.
            value (str): Value for the header. Must be convertable to
                ``str`` or be of type ``str`` or
                ``StringType``. Strings must contain only US-ASCII characters.
                Under Python 2.x, the ``unicode`` type is also accepted,
                although such strings are also limited to US-ASCII.

        Raises:
            ValueError: `name` cannot be ``'Set-Cookie'``.
        """

        # NOTE(kgriffs): uwsgi fails with a TypeError if any header
        # is not a str, so do the conversion here. It's actually
        # faster to not do an isinstance check. str() will encode
        # to US-ASCII.
        name = str(name)
        value = str(value)

        # NOTE(kgriffs): normalize name by lowercasing it
        name = name.lower()

        if name == 'set-cookie':
            raise HeaderNotSupported('This method cannot be used to set cookies')

        self._headers[name] = value

    def delete_header(self, name):
        """Delete a header that was previously set for this response.

        If the header was not previously set, nothing is done (no error is
        raised). Otherwise, all values set for the header will be removed
        from the response.

        Note that calling this method is equivalent to setting the
        corresponding header property (when said property is available) to
        ``None``. For example::

            resp.etag = None

        Warning:
            This method cannot be used with the Set-Cookie header. Instead,
            use :meth:`~.unset_cookie` to remove a cookie and ensure that the
            user agent expires its own copy of the data as well.

        Args:
            name (str): Header name (case-insensitive).  Must be of type
                ``str`` or ``StringType`` and contain only US-ASCII characters.
                Under Python 2.x, the ``unicode`` type is also accepted,
                although such strings are also limited to US-ASCII.

        Raises:
            ValueError: `name` cannot be ``'Set-Cookie'``.
        """

        # NOTE(kgriffs): normalize name by lowercasing it
        name = name.lower()

        if name == 'set-cookie':
            raise HeaderNotSupported('This method cannot be used to remove cookies')

        self._headers.pop(name, None)

    def append_header(self, name, value):
        """Set or append a header for this response.

        If the header already exists, the new value will normally be appended
        to it, delimited by a comma. The notable exception to this rule is
        Set-Cookie, in which case a separate header line for each value will be
        included in the response.

        Note:
            While this method can be used to efficiently append raw
            Set-Cookie headers to the response, you may find
            :py:meth:`~.set_cookie` to be more convenient.

        Args:
            name (str): Header name (case-insensitive). The restrictions
                noted below for the header's value also apply here.
            value (str): Value for the header. Must be convertable to
                ``str`` or be of type ``str`` or
                ``StringType``. Strings must contain only US-ASCII characters.
                Under Python 2.x, the ``unicode`` type is also accepted,
                although such strings are also limited to US-ASCII.
        """

        # NOTE(kgriffs): uwsgi fails with a TypeError if any header
        # is not a str, so do the conversion here. It's actually
        # faster to not do an isinstance check. str() will encode
        # to US-ASCII.
        name = str(name)
        value = str(value)

        # NOTE(kgriffs): normalize name by lowercasing it
        name = name.lower()

        if name == 'set-cookie':
            if not self._extra_headers:
                self._extra_headers = [(name, value)]
            else:
                self._extra_headers.append((name, value))
        else:
            if name in self._headers:
                value = self._headers[name] + ', ' + value

            self._headers[name] = value

    def set_headers(self, headers):
        """Set several headers at once.

        This method can be used to set a collection of raw header names and
        values all at once.

        Warning:
            Calling this method overwrites any existing values for the given
            header. If a list containing multiple instances of the same header
            is provided, only the last value will be used. To add multiple
            values to the response for a given header, see
            :meth:`~.append_header`.

        Warning:
            This method cannot be used to set cookies; instead, use
            :meth:`~.append_header` or :meth:`~.set_cookie`.

        Args:
            headers (dict or list): A dictionary of header names and values
                to set, or a ``list`` of (*name*, *value*) tuples. Both *name*
                and *value* must be of type ``str`` or ``StringType`` and
                contain only US-ASCII characters. Under Python 2.x, the
                ``unicode`` type is also accepted, although such strings are
                also limited to US-ASCII.

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
            # NOTE(kgriffs): uwsgi fails with a TypeError if any header
            # is not a str, so do the conversion here. It's actually
            # faster to not do an isinstance check. str() will encode
            # to US-ASCII.
            name = str(name)
            value = str(value)

            name = name.lower()

            if name == 'set-cookie':
                raise HeaderNotSupported('This method cannot be used to set cookies')

            _headers[name] = value

    def add_link(self, target, rel, title=None, title_star=None,
                 anchor=None, hreflang=None, type_hint=None):
        """Add a link header to the response.

        (See also: RFC 5988, Section 1)

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
                "bookmark".

                (See also: http://www.iana.org/assignments/link-relations/link-relations.xhtml)

        Keyword Args:
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
            if isinstance(hreflang, compat.string_types):
                value += '; hreflang=' + hreflang
            else:
                value += '; '
                value += '; '.join(['hreflang=' + lang for lang in hreflang])

        if anchor is not None:
            value += '; anchor="' + uri_encode(anchor) + '"'

        # NOTE(kgriffs): uwsgi fails with a TypeError if any header
        # is not a str, so do the conversion here. It's actually
        # faster to not do an isinstance check. str() will encode
        # to US-ASCII.
        value = str(value)

        _headers = self._headers
        if 'link' in _headers:
            _headers['link'] += ', ' + value
        else:
            _headers['link'] = value

    cache_control = header_property(
        'Cache-Control',
        """Set the Cache-Control header.

        Used to set a list of cache directives to use as the value of the
        Cache-Control header. The list will be joined with ", " to produce
        the value for the header.

        """,
        format_header_value_list)

    content_location = header_property(
        'Content-Location',
        """Set the Content-Location header.

        This value will be URI encoded per RFC 3986. If the value that is
        being set is already URI encoded it should be decoded first or the
        header should be set manually using the set_header method.
        """,
        uri_encode)

    content_length = header_property(
        'Content-Length',
        """Set the Content-Length header.

        This property can be used for responding to HEAD requests when you
        aren't actually providing the response body, or when streaming the
        response. If either the `body` property or the `data` property is set
        on the response, the framework will force Content-Length to be the
        length of the given body bytes. Therefore, it is only necessary to
        manually set the content length when those properties are not used.

        Note:
            In cases where the response content is a stream (readable
            file-like object), Falcon will not supply a Content-Length header
            to the WSGI server unless `content_length` is explicitly set.
            Consequently, the server may choose to use chunked encoding or one of the
            other strategies suggested by PEP-3333.

        """,
    )

    # TODO(kgriffs): Remove deprecated alias once development opens for 3.0
    stream_len = content_length

    content_range = header_property(
        'Content-Range',
        """A tuple to use in constructing a value for the Content-Range header.

        The tuple has the form (*start*, *end*, *length*, [*unit*]), where *start* and
        *end* designate the range (inclusive), and *length* is the
        total length, or '\\*' if unknown. You may pass ``int``'s for
        these numbers (no need to convert to ``str`` beforehand). The optional value
        *unit* describes the range unit and defaults to 'bytes'

        Note:
            You only need to use the alternate form, 'bytes \\*/1234', for
            responses that use the status '416 Range Not Satisfiable'. In this
            case, raising ``falcon.HTTPRangeNotSatisfiable`` will do the right
            thing.

        (See also: RFC 7233, Section 4.2)
        """,
        format_range)

    content_type = header_property(
        'Content-Type',
        """Sets the Content-Type header.

        The ``falcon`` module provides a number of constants for
        common media types, including ``falcon.MEDIA_JSON``,
        ``falcon.MEDIA_MSGPACK``, ``falcon.MEDIA_YAML``,
        ``falcon.MEDIA_XML``, ``falcon.MEDIA_HTML``,
        ``falcon.MEDIA_JS``, ``falcon.MEDIA_TEXT``,
        ``falcon.MEDIA_JPEG``, ``falcon.MEDIA_PNG``,
        and ``falcon.MEDIA_GIF``.
        """)

    downloadable_as = header_property(
        'Content-Disposition',
        """Set the Content-Disposition header using the given filename.

        The value will be used for the *filename* directive. For example,
        given ``'report.pdf'``, the Content-Disposition header would be set
        to: ``'attachment; filename="report.pdf"'``.
        """,
        format_content_disposition)

    etag = header_property(
        'ETag',
        """Set the ETag header.

        The ETag header will be wrapped with double quotes ``"value"`` in case
        the user didn't pass it.
        """,
        format_etag_header)

    expires = header_property(
        'Expires',
        """Set the Expires header. Set to a ``datetime`` (UTC) instance.

        Note:
            Falcon will format the ``datetime`` as an HTTP date string.
        """,
        dt_to_http)

    last_modified = header_property(
        'Last-Modified',
        """Set the Last-Modified header. Set to a ``datetime`` (UTC) instance.

        Note:
            Falcon will format the ``datetime`` as an HTTP date string.
        """,
        dt_to_http)

    location = header_property(
        'Location',
        """Set the Location header.

        This value will be URI encoded per RFC 3986. If the value that is
        being set is already URI encoded it should be decoded first or the
        header should be set manually using the set_header method.
        """,
        uri_encode)

    retry_after = header_property(
        'Retry-After',
        """Set the Retry-After header.

        The expected value is an integral number of seconds to use as the
        value for the header. The HTTP-date syntax is not supported.
        """,
        str)

    vary = header_property(
        'Vary',
        """Value to use for the Vary header.

        Set this property to an iterable of header names. For a single
        asterisk or field value, simply pass a single-element ``list``
        or ``tuple``.

        The "Vary" header field in a response describes what parts of
        a request message, aside from the method, Host header field,
        and request target, might influence the origin server's
        process for selecting and representing this response.  The
        value consists of either a single asterisk ("*") or a list of
        header field names (case-insensitive).

        (See also: RFC 7231, Section 7.1.4)
        """,
        format_header_value_list)

    accept_ranges = header_property(
        'Accept-Ranges',
        """Set the Accept-Ranges header.

        The Accept-Ranges header field indicates to the client which
        range units are supported (e.g. "bytes") for the target
        resource.

        If range requests are not supported for the target resource,
        the header may be set to "none" to advise the client not to
        attempt any such requests.

        Note:
            "none" is the literal string, not Python's built-in ``None``
            type.

        """)

    def _set_media_type(self, media_type=None):
        """Wrapper around set_header to set a content-type.

        Args:
            media_type: Media type to use for the Content-Type
                header.

        """

        # PERF(kgriffs): Using "in" like this is faster than using
        # dict.setdefault (tested on py27).
        set_content_type = (media_type is not None and
                            'content-type' not in self._headers)

        if set_content_type:
            self.set_header('content-type', media_type)

    def _wsgi_headers(self, media_type=None, py2=compat.PY2):
        """Convert headers into the format expected by WSGI servers.

        Args:
            media_type: Default media type to use for the Content-Type
                header if the header was not set explicitly (default ``None``).

        """

        headers = self._headers
        # PERF(vytas): uglier inline version of Response._set_media_type
        if media_type is not None and 'content-type' not in headers:
            headers['content-type'] = media_type

        if py2:
            # PERF(kgriffs): Don't create an extra list object if
            # it isn't needed.
            items = headers.items()
        else:
            items = list(headers.items())

        if self._extra_headers:
            items += self._extra_headers

        # NOTE(kgriffs): It is important to append these after self._extra_headers
        #   in case the latter contains Set-Cookie headers that should be
        #   overridden by a call to unset_cookie().
        if self._cookies is not None:
            # PERF(tbug):
            # The below implementation is ~23% faster than
            # the alternative:
            #
            #     self._cookies.output().split("\\r\\n")
            #
            # Even without the .split("\\r\\n"), the below
            # is still ~17% faster, so don't use .output()
            items += [('set-cookie', c.OutputString())
                      for c in self._cookies.values()]
        return items


class ResponseOptions(object):
    """Defines a set of configurable response options.

    An instance of this class is exposed via :any:`API.resp_options` for
    configuring certain :py:class:`~.Response` behaviors.

    Attributes:
        secure_cookies_by_default (bool): Set to ``False`` in development
            environments to make the `secure` attribute for all cookies
            default to ``False``. This can make testing easier by
            not requiring HTTPS. Note, however, that this setting can
            be overridden via `set_cookie()`'s `secure` kwarg.

        default_media_type (str): The default Internet media type (RFC 2046) to
            use when deserializing a response. This value is normally set to the
            media type provided when a :class:`falcon.API` is initialized;
            however, if created independently, this will default to the
            ``DEFAULT_MEDIA_TYPE`` specified by Falcon.

        media_handlers (Handlers): A dict-like object that allows you to
            configure the media-types that you would like to handle.
            By default, a handler is provided for the ``application/json``
            media type.

        static_media_types (dict): A mapping of dot-prefixed file extensions to
            Internet media types (RFC 2046). Defaults to ``mimetypes.types_map``
            after calling ``mimetypes.init()``.
    """
    __slots__ = (
        'secure_cookies_by_default',
        'default_media_type',
        'media_handlers',
        'static_media_types',
    )

    def __init__(self):
        self.secure_cookies_by_default = True
        self.default_media_type = DEFAULT_MEDIA_TYPE
        self.media_handlers = Handlers()

        mimetypes.init()
        self.static_media_types = mimetypes.types_map
