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

from __future__ import annotations

from datetime import datetime
from datetime import timezone
import functools
import mimetypes
from typing import (
    Any,
    ClassVar,
    Dict,
    Iterable,
    List,
    Mapping,
    NoReturn,
    Optional,
    overload,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)

from falcon._typing import _UNSET
from falcon._typing import RangeSetHeader
from falcon._typing import UnsetOr
from falcon.constants import _DEFAULT_STATIC_MEDIA_TYPES
from falcon.constants import DEFAULT_MEDIA_TYPE
from falcon.errors import HeaderNotSupported
from falcon.media import Handlers
from falcon.response_helpers import _format_content_disposition
from falcon.response_helpers import _format_etag_header
from falcon.response_helpers import _format_header_value_list
from falcon.response_helpers import _format_range
from falcon.response_helpers import _header_property
from falcon.response_helpers import _is_ascii_encodable
from falcon.typing import Headers
from falcon.typing import ReadableIO
from falcon.util import dt_to_http
from falcon.util import http_cookies
from falcon.util import http_status_to_code
from falcon.util import structures
from falcon.util.deprecation import AttributeRemovedError
from falcon.util.uri import encode_check_escaped as uri_encode
from falcon.util.uri import encode_value_check_escaped as uri_encode_value

if TYPE_CHECKING:
    import http


_RESERVED_CROSSORIGIN_VALUES = frozenset({'anonymous', 'use-credentials'})
_RESERVED_SAMESITE_VALUES = frozenset({'lax', 'strict', 'none'})


class Response:
    """Represents an HTTP response to a client request.

    Note:
        ``Response`` is not meant to be instantiated directly by responders.

    Keyword Arguments:
        options (ResponseOptions): Set of global options passed from the App handler.
    """

    __slots__ = (
        'text',
        'context',
        'options',
        'status',
        'stream',
        '_cookies',
        '_data',
        '_extra_headers',
        '_headers',
        '_media',
        '_media_rendered',
        '__dict__',
    )

    _cookies: Optional[http_cookies.SimpleCookie]
    _data: Optional[bytes]
    _extra_headers: Optional[List[Tuple[str, str]]]
    _headers: Headers
    _media: Optional[Any]
    _media_rendered: UnsetOr[bytes]

    # Child classes may override this
    context_type: ClassVar[Type[structures.Context]] = structures.Context
    """Class variable that determines the factory or
    type to use for initializing the `context` attribute. By default,
    the framework will instantiate bare objects (instances of the bare
    :class:`falcon.Context` class). However, you may override this
    behavior by creating a custom child class of
    :class:`falcon.Response`, and then passing that new class to
    ``falcon.App()`` by way of the latter's `response_type` parameter.

    Note:
        When overriding `context_type` with a factory function (as
        opposed to a class), the function is called like a method of
        the current Response instance. Therefore the first argument is
        the Response instance itself (self).
    """

    # Attribute declaration
    complete: bool = False
    """Set to ``True`` from within a middleware method to signal to the framework that
    request processing should be short-circuited (see also
    :ref:`Middleware <middleware>`).
    """
    status: Union[str, int, http.HTTPStatus]
    """HTTP status code or line (e.g., ``'200 OK'``).

    This may be set to a member of :class:`http.HTTPStatus`, an HTTP status line
    string (e.g., ``'200 OK'``), or an ``int``.

    Note:
        The Falcon framework itself provides a number of constants for
        common status codes. They all start with the ``HTTP_`` prefix,
        as in: ``falcon.HTTP_204``. (See also: :ref:`status`.)
    """
    text: Optional[str]
    """String representing response content.

    Note:
        Falcon will encode the given text as UTF-8 in the response. If the content
        is already a byte string, use the :attr:`data` attribute instead (it's faster).
    """
    stream: Union[ReadableIO, Iterable[bytes], None]
    """Either a file-like object with a `read()` method that takes an optional size
    argument and returns a block of bytes, or an iterable object, representing response
    content, and yielding blocks as byte strings. Falcon will use *wsgi.file_wrapper*,
    if provided by the WSGI server, in order to efficiently serve file-like objects.

    Note:
        If the stream is set to an iterable object that requires
        resource cleanup, it can implement a close() method to do so.
        The close() method will be called upon completion of the request.
    """
    context: structures.Context
    """Empty object to hold any data (in its attributes) about the response which is
    specific to your app (e.g. session object).
    Falcon itself will not interact with this attribute after it has been initialized.

    Note:
        The preferred way to pass response-specific data, when using the
        default context type, is to set attributes directly on the
        `context` object. For example::

            resp.context.cache_strategy = 'lru'
    """
    options: ResponseOptions
    """Set of global options passed in from the App handler."""

    def __init__(self, options: Optional[ResponseOptions] = None) -> None:
        self.status = '200 OK'
        self._headers = {}

        # NOTE(kgriffs): Collection of additional headers as a list of raw
        #   tuples, to use in cases where we need more control over setting
        #   headers and duplicates are allowable or even necessary.
        #
        # PERF(kgriffs): Save some CPU cycles and a few bytes of RAM by
        #   only instantiating the list object later on IFF it is needed.
        self._extra_headers = None

        self.options = options if options is not None else ResponseOptions()

        # NOTE(tbug): will be set to a SimpleCookie object
        # when cookie is set via set_cookie
        self._cookies = None

        self.text = None
        self.stream = None
        self._data = None
        self._media = None
        self._media_rendered = _UNSET

        self.context = self.context_type()

    @property
    def status_code(self) -> int:
        """HTTP status code normalized from :attr:`status`.

        When a code is assigned to this property, :attr:`status` is updated,
        and vice-versa. The status code can be useful when needing to check
        in middleware for codes that fall into a certain class, e.g.::

            if resp.status_code >= 400:
                log.warning(f'returning error response: {resp.status_code}')
        """
        return http_status_to_code(self.status)

    @status_code.setter
    def status_code(self, value: int) -> None:
        self.status = value

    @property
    def body(self) -> NoReturn:
        raise AttributeRemovedError(
            'The body attribute is no longer supported. '
            'Please use the text attribute instead.'
        )

    @body.setter
    def body(self, value: str) -> NoReturn:
        raise AttributeRemovedError(
            'The body attribute is no longer supported. '
            'Please use the text attribute instead.'
        )

    @property
    def data(self) -> Optional[bytes]:
        """Byte string representing response content.

        Use this attribute in lieu of `text` when your content is
        already a byte string (of type ``bytes``). See also the note below.

        Warning:
            Always use the `text` attribute for text, or encode it
            first to ``bytes`` when using the `data` attribute, to
            ensure Unicode characters are properly encoded in the
            HTTP response.
        """
        return self._data

    @data.setter
    def data(self, value: Optional[bytes]) -> None:
        self._data = value

    @property
    def headers(self) -> Headers:
        """Copy of all headers set for the response, without cookies.

        Note that a new copy is created and returned each time this property is
        referenced.
        """
        return self._headers.copy()

    @property
    def media(self) -> Any:
        """A serializable object supported by the media handlers configured via
        :class:`falcon.RequestOptions`.

        Note:
            See also :ref:`media` for more information regarding media
            handling.
        """  # noqa D205
        return self._media

    @media.setter
    def media(self, value: Any) -> None:
        self._media = value
        self._media_rendered = _UNSET

    def render_body(self) -> Optional[bytes]:
        """Get the raw bytestring content for the response body.

        This method returns the raw data for the HTTP response body, taking
        into account the :attr:`~.text`, :attr:`~.data`, and :attr:`~.media`
        attributes.

        Note:
            This method ignores :attr:`~.stream`; the caller must check
            and handle that attribute directly.

        Returns:
            bytes: The UTF-8 encoded value of the `text` attribute, if
            set. Otherwise, the value of the `data` attribute if set, or
            finally the serialized value of the `media` attribute. If
            none of these attributes are set, ``None`` is returned.
        """
        data: Optional[bytes]
        text = self.text
        if text is None:
            data = self._data

            if data is None and self._media is not None:
                # NOTE(kgriffs): We use a special _UNSET singleton since
                #   None is ambiguous (the media handler might return None).
                if self._media_rendered is _UNSET:
                    if not self.content_type:
                        self.content_type = self.options.default_media_type

                    handler, _, _ = self.options.media_handlers._resolve(
                        self.content_type, self.options.default_media_type
                    )

                    self._media_rendered = handler.serialize(
                        self._media, self.content_type
                    )

                data = self._media_rendered
        else:
            try:
                # NOTE(kgriffs): Normally we expect text to be a string
                data = text.encode()
            except AttributeError:
                # NOTE(kgriffs): Assume it was a bytes object already
                data = text  # type: ignore[assignment]

        return data

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.status}>'

    def set_stream(
        self, stream: Union[ReadableIO, Iterable[bytes]], content_length: int
    ) -> None:
        """Set both `stream` and `content_length`.

        Although the :attr:`~falcon.Response.stream` and
        :attr:`~falcon.Response.content_length` properties may be set
        directly, using this method ensures
        :attr:`~falcon.Response.content_length` is not accidentally
        neglected when the length of the stream is known in advance. Using this
        method is also slightly more performant as compared to setting the
        properties individually.

        Note:
            If the stream length is unknown, you can set
            :attr:`~falcon.Response.stream` directly, and ignore
            :attr:`~falcon.Response.content_length`. In this case, the ASGI
            server may choose to use chunked encoding or one
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

    def set_cookie(  # noqa: C901
        self,
        name: str,
        value: str,
        expires: Optional[datetime] = None,
        max_age: Optional[int] = None,
        domain: Optional[str] = None,
        path: Optional[str] = None,
        secure: Optional[bool] = None,
        http_only: bool = True,
        same_site: Optional[str] = None,
        partitioned: bool = False,
    ) -> None:
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

                Note:
                    Cookies do not provide isolation by port, so the domain
                    should not provide one. (See also: RFC 6265, Section 8.5)

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
                    :attr:`~.ResponseOptions.secure_cookies_by_default`
                    via :any:`App.resp_options`.

                Warning:
                    For the `secure` cookie attribute to be effective,
                    your application will need to enforce HTTPS.

                (See also: RFC 6265, Section 4.1.2.5)

            http_only (bool): The HttpOnly attribute limits the scope of the
                cookie to HTTP requests.  In particular, the attribute
                instructs the user agent to omit the cookie when providing
                access to cookies via "non-HTTP" APIs. This is intended to
                mitigate some forms of cross-site scripting. (default: ``True``)

                Note:
                    HttpOnly cookies are not visible to javascript scripts
                    in the browser. They are automatically sent to the server
                    on javascript ``XMLHttpRequest`` or ``Fetch`` requests.

                (See also: RFC 6265, Section 4.1.2.6)

            same_site (str): Helps protect against CSRF attacks by restricting
                when a cookie will be attached to the request by the user agent.
                When set to ``'Strict'``, the cookie will only be sent along
                with "same-site" requests.  If the value is ``'Lax'``, the
                cookie will be sent with same-site requests, and with
                "cross-site" top-level navigations.  If the value is ``'None'``,
                the cookie will be sent with same-site and cross-site requests.
                Finally, when this attribute is not set on the cookie, the
                attribute will be treated as if it had been set to ``'None'``.

                (See also: `Same-Site RFC Draft`_)

            partitioned (bool): Prevents cookies from being accessed from other
                subdomains. With partitioned enabled, a cookie set by
                https://3rd-party.example which is embedded inside
                https://site-a.example can no longer be accessed by
                https://site-b.example. While this attribute is not yet
                standardized, it is already used by Chrome.

                (See also: `CHIPS`_)

                .. versionadded:: 4.0

        Raises:
            KeyError: `name` is not a valid cookie name.
            ValueError: `value` is not a valid cookie value.

        .. _RFC 6265:
            http://tools.ietf.org/html/rfc6265

        .. _Same-Site RFC Draft:
            https://tools.ietf.org/html/draft-ietf-httpbis-rfc6265bis-03#section-4.1.2.7

        .. _CHIPS:
            https://developer.mozilla.org/en-US/docs/Web/Privacy/Privacy_sandbox/Partitioned_cookies

        """

        if not _is_ascii_encodable(name):
            raise KeyError('name is not ascii encodable')
        if not _is_ascii_encodable(value):
            raise ValueError('value is not ascii encodable')

        value = str(value)

        if self._cookies is None:
            self._cookies = http_cookies.SimpleCookie()

        try:
            self._cookies[name] = value
        except http_cookies.CookieError as e:  # pragma: no cover
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
                gmt_expires = expires.astimezone(timezone.utc)
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

        is_secure = self.options.secure_cookies_by_default if secure is None else secure

        if is_secure:
            self._cookies[name]['secure'] = True

        if http_only:
            self._cookies[name]['httponly'] = http_only

        # PERF(kgriffs): Morsel.__setitem__() will lowercase this anyway,
        #   so we can just pass this in and when __setitem__() calls
        #   lower() it will be very slightly faster.
        if same_site:
            same_site = same_site.lower()

            if same_site not in _RESERVED_SAMESITE_VALUES:
                raise ValueError(
                    "same_site must be set to either 'lax', 'strict', or 'none'"
                )

            self._cookies[name]['samesite'] = same_site.capitalize()

        if partitioned:
            self._cookies[name]['partitioned'] = True

    def unset_cookie(
        self,
        name: str,
        samesite: str = 'Lax',
        domain: Optional[str] = None,
        path: Optional[str] = None,
    ) -> None:
        """Unset a cookie in the response.

        Clears the contents of the cookie, and instructs the user
        agent to immediately expire its own copy of the cookie.

        Note:
            Modern browsers place restriction on cookies without the
            "same-site" cookie attribute set. To that end this attribute
            is set to ``'Lax'`` by this method.

            (See also: `Same-Site warnings`_)

        Warning:
            In order to successfully remove a cookie, both the
            path and the domain must match the values that were
            used when the cookie was created.

        Args:
            name (str): Cookie name

        Keyword Args:
            samesite (str): Allows to override the default 'Lax' same_site
                    setting for the unset cookie.

                    .. versionadded:: 4.0

            domain (str): Restricts the cookie to a specific domain and
                    any subdomains of that domain. By default, the user
                    agent will return the cookie only to the origin server.
                    When overriding this default behavior, the specified
                    domain must include the origin server. Otherwise, the
                    user agent will reject the cookie.

                    Note:
                        Cookies do not provide isolation by port, so the domain
                        should not provide one. (See also: RFC 6265, Section 8.5)

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

        .. _Same-Site warnings:
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite#Fixing_common_warnings
        """  # noqa: E501
        if self._cookies is None:
            self._cookies = http_cookies.SimpleCookie()

        self._cookies[name] = ''

        # NOTE(Freezerburn): SimpleCookie apparently special cases the
        # expires attribute to automatically use strftime and set the
        # time as a delta from the current time. We use -1 here to
        # basically tell the browser to immediately expire the cookie,
        # thus removing it from future request objects.
        self._cookies[name]['expires'] = -1

        # NOTE(CaselIT): Set SameSite to Lax to avoid setting invalid cookies.
        # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite#Fixing_common_warnings  # noqa: E501
        self._cookies[name]['samesite'] = samesite

        if domain:
            self._cookies[name]['domain'] = domain

        if path:
            self._cookies[name]['path'] = path

    @overload
    def get_header(self, name: str, default: str) -> str: ...

    @overload
    def get_header(self, name: str, default: Optional[str] = ...) -> Optional[str]: ...

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
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

    def set_header(self, name: str, value: str) -> None:
        """Set a header for this response to a given value.

        Warning:
            Calling this method overwrites any values already set for this
            header. To append an additional value for this header, use
            :meth:`~.append_header` instead.

        Warning:
            This method cannot be used to set cookies; instead, use
            :meth:`~.append_header` or :meth:`~.set_cookie`.

        Args:
            name (str): Header name (case-insensitive). The name may contain
                only US-ASCII characters.
            value (str): Value for the header. As with the header's name, the
                value may contain only US-ASCII characters.

        Raises:
            ValueError: `name` cannot be ``'Set-Cookie'``.
        """

        # NOTE(kgriffs): uwsgi fails with a TypeError if any header
        # is not a str, so do the conversion here. It's actually
        # faster to not do an isinstance check. str() will encode
        # to US-ASCII.
        value = str(value)

        # NOTE(kgriffs): normalize name by lowercasing it
        name = name.lower()

        if name == 'set-cookie':
            raise HeaderNotSupported('This method cannot be used to set cookies')

        self._headers[name] = value

    def delete_header(self, name: str) -> None:
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
            name (str): Header name (case-insensitive). The name may
                contain only US-ASCII characters.

        Raises:
            ValueError: `name` cannot be ``'Set-Cookie'``.
        """

        # NOTE(kgriffs): normalize name by lowercasing it
        name = name.lower()

        if name == 'set-cookie':
            raise HeaderNotSupported('This method cannot be used to remove cookies')

        self._headers.pop(name, None)

    def append_header(self, name: str, value: str) -> None:
        """Set or append a header for this response.

        If the header already exists, the new value will normally be appended
        to it, delimited by a comma. The notable exception to this rule is
        Set-Cookie, in which case a separate header line for each value will be
        included in the response.

        Note:
            While this method can be used to efficiently append raw
            Set-Cookie headers to the response, you may find
            :meth:`~.set_cookie` to be more convenient.

        Args:
            name (str): Header name (case-insensitive). The name may contain
                only US-ASCII characters.
            value (str): Value for the header. As with the header's name, the
                value may contain only US-ASCII characters.
        """

        # NOTE(kgriffs): uwsgi fails with a TypeError if any header
        # is not a str, so do the conversion here. It's actually
        # faster to not do an isinstance check. str() will encode
        # to US-ASCII.
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

    def set_headers(
        self, headers: Union[Mapping[str, str], Iterable[Tuple[str, str]]]
    ) -> None:
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
            headers (Iterable[[str, str]]): An iterable of ``[name, value]`` two-member
                iterables, or a dict-like object that implements an ``items()`` method.
                Both *name* and *value* must be of type ``str`` and
                contain only US-ASCII characters.

                Note:
                    Falcon can process an iterable of tuples slightly faster
                    than a dict.

        Raises:
            ValueError: `headers` was not a ``dict`` or ``list`` of ``tuple``
                         or ``Iterable[[str, str]]``.
        """

        header_items = getattr(headers, 'items', None)

        if callable(header_items):
            headers = header_items()

        # NOTE(kgriffs): We can't use dict.update because we have to
        # normalize the header names.
        _headers = self._headers

        for name, value in headers:  # type: ignore[misc]
            # NOTE(kgriffs): uwsgi fails with a TypeError if any header
            # is not a str, so do the conversion here. It's actually
            # faster to not do an isinstance check. str() will encode
            # to US-ASCII.
            value = str(value)

            name = name.lower()
            if name == 'set-cookie':
                raise HeaderNotSupported('This method cannot be used to set cookies')

            _headers[name] = value

    def append_link(
        self,
        target: str,
        rel: str,
        title: Optional[str] = None,
        title_star: Optional[Tuple[str, str]] = None,
        anchor: Optional[str] = None,
        hreflang: Optional[Union[str, Iterable[str]]] = None,
        type_hint: Optional[str] = None,
        crossorigin: Optional[str] = None,
        link_extension: Optional[Iterable[Tuple[str, str]]] = None,
    ) -> None:
        """Append a link header to the response.

        (See also: RFC 5988, Section 1)

        Note:
            Calling this method repeatedly will cause each link to be
            appended to the Link header value, separated by commas.

        Args:
            target (str): Target IRI for the resource identified by the
                link. Will be converted to a URI, if necessary, per
                RFC 3987, Section 3.1.
            rel (str): Relation type of the link, such as "next" or
                "bookmark".

                (See also:
                http://www.iana.org/assignments/link-relations/link-relations.xhtml)

        Keyword Args:
            title (str): Human-readable label for the destination of
                the link (default ``None``). If the title includes non-ASCII
                characters, you will need to use `title_star` instead, or
                provide both a US-ASCII version using `title` and a
                Unicode version using `title_star`.
            title_star (tuple[str, str]): Localized title describing the
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
                    *text* will always be encoded as UTF-8.

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
            crossorigin(str):  Determines how cross origin requests are handled.
                Can take values 'anonymous' or 'use-credentials' or None.
                (See:
                https://www.w3.org/TR/html50/infrastructure.html#cors-settings-attribute)
            link_extension: Provides additional custom attributes, as
                described in RFC 8288, Section 3.4.2; each member of the iterable
                must be a two-tuple in the form of (*param*, *value*).

        """

        # PERF(kgriffs): Heuristic to detect possibility of an extension
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
                rel = '"' + ' '.join([uri_encode(r) for r in rel.split()]) + '"'
            else:
                rel = f'"{uri_encode(rel)}"'

        value = '<' + uri_encode(target) + '>; rel=' + rel

        if title is not None:
            value += f'; title="{title}"'

        if title_star is not None:
            value += f"; title*=UTF-8'{title_star[0]}'{uri_encode_value(title_star[1])}"

        if type_hint is not None:
            value += f'; type="{type_hint}"'

        if hreflang is not None:
            if isinstance(hreflang, str):
                value += f'; hreflang={hreflang}'
            else:
                value += '; '
                value += '; '.join(['hreflang=' + lang for lang in hreflang])

        if anchor is not None:
            value += f'; anchor="{uri_encode(anchor)}"'

        if crossorigin is not None:
            crossorigin = crossorigin.lower()
            if crossorigin not in _RESERVED_CROSSORIGIN_VALUES:
                raise ValueError(
                    "crossorigin must be set to either 'anonymous' or 'use-credentials'"
                )
            if crossorigin == 'anonymous':
                value += '; crossorigin'
            else:  # crossorigin == 'use-credentials'
                # PERF(vytas): the only remaining value is inlined.
                # Un-inline in case more values are supported in the future.
                value += '; crossorigin="use-credentials"'

        if link_extension is not None:
            value += '; '
            value += '; '.join([f'{p}={v}' for p, v in link_extension])

        _headers = self._headers
        if 'link' in _headers:
            _headers['link'] += f', {value}'
        else:
            _headers['link'] = value

    @property
    def add_link(self) -> NoReturn:
        raise AttributeRemovedError(
            'The add_link() method is no longer supported. '
            'Please use append_link() instead.'
        )

    cache_control: Union[str, Iterable[str], None] = _header_property(
        'Cache-Control',
        """Set the Cache-Control header.

        Used to set a list of cache directives to use as the value of the
        Cache-Control header. The list will be joined with ", " to produce
        the value for the header.
        """,
        _format_header_value_list,
    )
    """Set the Cache-Control header.

    Used to set a list of cache directives to use as the value of the
    Cache-Control header. The list will be joined with ", " to produce
    the value for the header.
    """

    content_location: Optional[str] = _header_property(
        'Content-Location',
        """Set the Content-Location header.

        This value will be URI encoded per RFC 3986. If the value that is
        being set is already URI encoded it should be decoded first or the
        header should be set manually using the set_header method.
        """,
        uri_encode,
    )
    """Set the Content-Location header.

    This value will be URI encoded per RFC 3986. If the value that is
    being set is already URI encoded it should be decoded first or the
    header should be set manually using the set_header method.
    """

    content_length: Union[str, int, None] = _header_property(
        'Content-Length',
        """Set the Content-Length header.

        This property can be used for responding to HEAD requests when you
        aren't actually providing the response body, or when streaming the
        response. If either the `text` property or the `data` property is set
        on the response, the framework will force Content-Length to be the
        length of the given text bytes. Therefore, it is only necessary to
        manually set the content length when those properties are not used.

        Note:
            In cases where the response content is a stream (readable
            file-like object), Falcon will not supply a Content-Length header
            to the server unless `content_length` is explicitly set.
            Consequently, the server may choose to use chunked encoding in this
            case.

        """,
    )
    """Set the Content-Length header.

    This property can be used for responding to HEAD requests when you
    aren't actually providing the response body, or when streaming the
    response. If either the `text` property or the `data` property is set
    on the response, the framework will force Content-Length to be the
    length of the given text bytes. Therefore, it is only necessary to
    manually set the content length when those properties are not used.

    Note:
        In cases where the response content is a stream (readable
        file-like object), Falcon will not supply a Content-Length header
        to the server unless `content_length` is explicitly set.
        Consequently, the server may choose to use chunked encoding in this
        case.

    """

    content_range: Union[str, RangeSetHeader, None] = _header_property(
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
        _format_range,
    )
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
    """

    content_type: Optional[str] = _header_property(
        'Content-Type',
        """Sets the Content-Type header.

        The ``falcon`` module provides a number of constants for
        common media types, including ``falcon.MEDIA_JSON``,
        ``falcon.MEDIA_MSGPACK``, ``falcon.MEDIA_YAML``,
        ``falcon.MEDIA_XML``, ``falcon.MEDIA_HTML``,
        ``falcon.MEDIA_JS``, ``falcon.MEDIA_TEXT``,
        ``falcon.MEDIA_JPEG``, ``falcon.MEDIA_PNG``,
        and ``falcon.MEDIA_GIF``.
        """,
    )
    """Sets the Content-Type header.

    The ``falcon`` module provides a number of constants for
    common media types, including ``falcon.MEDIA_JSON``,
    ``falcon.MEDIA_MSGPACK``, ``falcon.MEDIA_YAML``,
    ``falcon.MEDIA_XML``, ``falcon.MEDIA_HTML``,
    ``falcon.MEDIA_JS``, ``falcon.MEDIA_TEXT``,
    ``falcon.MEDIA_JPEG``, ``falcon.MEDIA_PNG``,
    and ``falcon.MEDIA_GIF``.
    """

    downloadable_as: Optional[str] = _header_property(
        'Content-Disposition',
        """Set the Content-Disposition header using the given filename.

        The value will be used for the ``filename`` directive. For example,
        given ``'report.pdf'``, the Content-Disposition header would be set
        to: ``'attachment; filename="report.pdf"'``.

        As per `RFC 6266 <https://tools.ietf.org/html/rfc6266#appendix-D>`_
        recommendations, non-ASCII filenames will be encoded using the
        ``filename*`` directive, whereas ``filename`` will contain the US
        ASCII fallback.
        """,
        functools.partial(_format_content_disposition, disposition_type='attachment'),
    )
    """Set the Content-Disposition header using the given filename.

    The value will be used for the ``filename`` directive. For example,
    given ``'report.pdf'``, the Content-Disposition header would be set
    to: ``'attachment; filename="report.pdf"'``.

    As per `RFC 6266 <https://tools.ietf.org/html/rfc6266#appendix-D>`_
    recommendations, non-ASCII filenames will be encoded using the
    ``filename*`` directive, whereas ``filename`` will contain the US
    ASCII fallback.
    """

    viewable_as: Optional[str] = _header_property(
        'Content-Disposition',
        """Set an inline Content-Disposition header using the given filename.

        The value will be used for the ``filename`` directive. For example,
        given ``'report.pdf'``, the Content-Disposition header would be set
        to: ``'inline; filename="report.pdf"'``.

        As per `RFC 6266 <https://tools.ietf.org/html/rfc6266#appendix-D>`_
        recommendations, non-ASCII filenames will be encoded using the
        ``filename*`` directive, whereas ``filename`` will contain the US
        ASCII fallback.

        .. versionadded:: 3.1
        """,
        functools.partial(_format_content_disposition, disposition_type='inline'),
    )
    """Set an inline Content-Disposition header using the given filename.

    The value will be used for the ``filename`` directive. For example,
    given ``'report.pdf'``, the Content-Disposition header would be set
    to: ``'inline; filename="report.pdf"'``.

    As per `RFC 6266 <https://tools.ietf.org/html/rfc6266#appendix-D>`_
    recommendations, non-ASCII filenames will be encoded using the
    ``filename*`` directive, whereas ``filename`` will contain the US
    ASCII fallback.

    .. versionadded:: 3.1
    """

    etag: Optional[str] = _header_property(
        'ETag',
        """Set the ETag header.

        The ETag header will be wrapped with double quotes ``"value"`` in case
        the user didn't pass it.
        """,
        _format_etag_header,
    )
    """Set the ETag header.

    The ETag header will be wrapped with double quotes ``"value"`` in case
    the user didn't pass it.
    """

    expires: Union[str, datetime, None] = _header_property(
        'Expires',
        """Set the Expires header. Set to a ``datetime`` (UTC) instance.

        Note:
            Falcon will format the ``datetime`` as an HTTP date string.
        """,
        dt_to_http,
    )
    """Set the Expires header. Set to a ``datetime`` (UTC) instance.

    Note:
        Falcon will format the ``datetime`` as an HTTP date string.
    """

    last_modified: Union[str, datetime, None] = _header_property(
        'Last-Modified',
        """Set the Last-Modified header. Set to a ``datetime`` (UTC) instance.

        Note:
            Falcon will format the ``datetime`` as an HTTP date string.
        """,
        dt_to_http,
    )
    """Set the Last-Modified header. Set to a ``datetime`` (UTC) instance.

    Note:
        Falcon will format the ``datetime`` as an HTTP date string.
    """

    location: Optional[str] = _header_property(
        'Location',
        """Set the Location header.

        This value will be URI encoded per RFC 3986. If the value that is
        being set is already URI encoded it should be decoded first or the
        header should be set manually using the set_header method.
        """,
        uri_encode,
    )
    """Set the Location header.

    This value will be URI encoded per RFC 3986. If the value that is
    being set is already URI encoded it should be decoded first or the
    header should be set manually using the set_header method.
    """

    retry_after: Union[int, str, None] = _header_property(
        'Retry-After',
        """Set the Retry-After header.

        The expected value is an integral number of seconds to use as the
        value for the header. The HTTP-date syntax is not supported.
        """,
    )
    """Set the Retry-After header.

    The expected value is an integral number of seconds to use as the
    value for the header. The HTTP-date syntax is not supported.
    """

    vary: Union[str, Iterable[str], None] = _header_property(
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
        _format_header_value_list,
    )
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
    """

    accept_ranges: Optional[str] = _header_property(
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

        """,
    )
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

    """

    def _set_media_type(self, media_type: Optional[str] = None) -> None:
        """Set a content-type; wrapper around set_header.

        Args:
            media_type: Media type to use for the Content-Type
                header.

        """

        # PERF(kgriffs): Using "in" like this is faster than dict.setdefault()
        #   in most cases, except on PyPy where it is only a fraction of a
        #   nanosecond slower. Last tested on Python versions 3.5-3.7.
        if media_type is not None and 'content-type' not in self._headers:
            self._headers['content-type'] = media_type

    def _wsgi_headers(self, media_type: Optional[str] = None) -> list[tuple[str, str]]:
        """Convert headers into the format expected by WSGI servers.

        Args:
            media_type: Default media type to use for the Content-Type
                header if the header was not set explicitly (default ``None``).

        """

        headers = self._headers
        # PERF(vytas): uglier inline version of Response._set_media_type
        if media_type is not None and 'content-type' not in headers:
            headers['content-type'] = media_type

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
            items += [('set-cookie', c.OutputString()) for c in self._cookies.values()]
        return items


class ResponseOptions:
    """Defines a set of configurable response options.

    An instance of this class is exposed via :attr:`falcon.App.resp_options`
    and :attr:`falcon.asgi.App.resp_options` for configuring certain
    :class:`~.Response` behaviors.
    """

    secure_cookies_by_default: bool
    """Set to ``False`` in development environments to make the ``secure`` attribute
    for all cookies. (default ``True``).

    This can make testing easier by not requiring HTTPS. Note, however, that this
    setting can be overridden via :meth:`~.Response.set_cookie()`'s ``secure`` kwarg.
    """
    default_media_type: str
    """The default Internet media type (RFC 2046) to use when rendering a response,
    when the Content-Type header is not set explicitly.

    This value is normally set to the media type provided when a :class:`falcon.App`
    is initialized; however, if created independently, this will default to
    :attr:`falcon.DEFAULT_MEDIA_TYPE`.
    """
    media_handlers: Handlers
    """A dict-like object for configuring the media-types to handle.

    Default handlers are provided for the ``application/json``,
    ``application/x-www-form-urlencoded`` and ``multipart/form-data`` media types.
    """
    static_media_types: Dict[str, str]
    """A mapping of dot-prefixed file extensions to Internet media types (RFC 2046).

    Defaults to ``mimetypes.types_map`` after calling ``mimetypes.init()``.
    """
    xml_error_serialization: bool
    """Set to ``False`` to disable automatic inclusion of the XML handler
    in the :ref:`default error serializer <errors>` (default ``True``).

    Enabling this option does not make Falcon automatically render all error
    responses in XML, but it is used only in the case the client prefers
    (via the ``Accept`` request header) XML to JSON and other configured media
    handlers.

    Note:
        Falcon 5.0 will either change the default to ``False``, or remove the
        automatic XML error serialization altogether.

    Note:
        This option has no effect when a custom error serializer, set using
        :meth:`~falcon.App.set_error_serializer`, is in use.

    .. versionadded:: 4.0
    """

    __slots__ = (
        'secure_cookies_by_default',
        'default_media_type',
        'media_handlers',
        'static_media_types',
        'xml_error_serialization',
    )

    def __init__(self) -> None:
        self.secure_cookies_by_default = True
        self.default_media_type = DEFAULT_MEDIA_TYPE
        self.media_handlers = Handlers()
        self.xml_error_serialization = True

        if not mimetypes.inited:
            mimetypes.init()
        self.static_media_types = mimetypes.types_map.copy()
        self.static_media_types.update(_DEFAULT_STATIC_MEDIA_TYPES)
