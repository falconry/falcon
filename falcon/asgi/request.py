# Copyright 2019-2020 by Kurt Griffiths
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

"""ASGI Request class."""

from __future__ import annotations

from typing import (
    Any,
    Awaitable,
    cast,
    Dict,
    List,
    Literal,
    Mapping,
    NoReturn,
    Optional,
    overload,
    Tuple,
    Union,
)

from falcon import errors
from falcon import request
from falcon import request_helpers as helpers
from falcon._typing import _UNSET
from falcon._typing import AsgiReceive
from falcon._typing import StoreArg
from falcon._typing import UnsetOr
from falcon.asgi_spec import AsgiEvent
from falcon.constants import SINGLETON_HEADERS
from falcon.forwarded import Forwarded
from falcon.util import deprecation
from falcon.util import ETag
from falcon.util.uri import parse_host
from falcon.util.uri import parse_query_string

from . import _request_helpers as asgi_helpers
from .stream import BoundedStream

__all__ = ('Request',)

_SINGLETON_HEADERS_BYTESTR = frozenset([h.encode() for h in SINGLETON_HEADERS])


class Request(request.Request):
    """Represents a client's HTTP request.

    Note:
        `Request` is not meant to be instantiated directly by responders.

    Args:
        scope (dict): ASGI HTTP connection scope passed in from the server (see
            also: `Connection Scope`_).
        receive (awaitable): ASGI awaitable callable that will yield a new
            event dictionary when one is available.

    Keyword Args:
        first_event (dict): First ASGI event received from the client,
            if one was preloaded (default ``None``).
        options (falcon.request.RequestOptions): Set of global request options
            passed from the App handler.

    .. _Connection Scope:
        https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope

    """

    __slots__ = [
        '_asgi_headers',
        # '_asgi_server_cached',
        # '_cached_headers',
        '_first_event',
        '_receive',
        # '_stream',
        'scope',
    ]

    # PERF(vytas): These boilerplates values will be shadowed when set on an
    #   instance. Avoiding a statement per each of those values allows to speed
    #   up __init__ substantially.
    _asgi_server_cached: Optional[Tuple[str, int]] = None
    _cached_access_route: Optional[List[str]] = None
    _cached_forwarded: Optional[List[Forwarded]] = None
    _cached_forwarded_prefix: Optional[str] = None
    _cached_forwarded_uri: Optional[str] = None
    _cached_headers: Optional[Dict[str, str]] = None
    # NOTE: _cached_headers_lower is not used
    _cached_prefix: Optional[str] = None
    _cached_relative_uri: Optional[str] = None
    _cached_uri: Optional[str] = None
    _media: UnsetOr[Any] = _UNSET
    _media_error: Optional[Exception] = None
    _stream: Optional[BoundedStream] = None

    scope: Dict[str, Any]
    """Reference to the ASGI HTTP connection scope passed in
    from the server (see also: `Connection Scope`_).

    .. _Connection Scope:
        https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope
    """
    is_websocket: bool
    """Set to ``True`` IFF this request was made as part of a WebSocket handshake."""

    def __init__(
        self,
        scope: Dict[str, Any],
        receive: AsgiReceive,
        first_event: Optional[AsgiEvent] = None,
        options: Optional[request.RequestOptions] = None,
    ):
        # =====================================================================
        # Prepare headers
        # =====================================================================

        req_headers: Dict[bytes, bytes] = {}
        for header_name, header_value in scope['headers']:
            # NOTE(kgriffs): According to ASGI 3.0, header names are always
            #   lowercased, and both name and value are byte strings. Although
            #   technically header names and values are restricted to US-ASCII
            #   we decode later (just-in-time) using the default 'utf-8' because
            #   it is a little faster than passing an encoding option (except
            #   under Cython).
            #
            #   The reason we wait to decode is that the typical app will not
            #   need to decode all request headers, and we usually can just
            #   leave the header name as a byte string and look it up that way.
            #

            # NOTE(kgriffs): There are no standard request headers that
            #   allow multiple instances to appear in the request while also
            #   disallowing list syntax.
            if (
                header_name not in req_headers
                or header_name in _SINGLETON_HEADERS_BYTESTR
            ):
                req_headers[header_name] = header_value
            else:
                req_headers[header_name] += b',' + header_value

        self._asgi_headers: Dict[bytes, bytes] = req_headers
        # PERF(vytas): Fall back to class variable(s) when unset.
        # self._cached_headers = None

        # =====================================================================
        #  Misc.
        # =====================================================================

        # PERF(vytas): Fall back to class variable(s) when unset.
        # self._asgi_server_cached = None  # Lazy
        self.scope = scope
        self.is_websocket = scope['type'] == 'websocket'

        self.options = options if options is not None else request.RequestOptions()

        self.method = 'GET' if self.is_websocket else scope['method']

        self.uri_template = None
        # PERF(vytas): Fall back to class variable(s) when unset.
        # self._media = _UNSET
        # self._media_error = None

        # TODO(kgriffs): ASGI does not specify whether 'path' may be empty,
        #   as was allowed for WSGI.
        path = scope['path'] or '/'

        if (
            self.options.strip_url_path_trailing_slash
            and len(path) != 1
            and path.endswith('/')
        ):
            self.path = path[:-1]
        else:
            self.path = path

        query_string = scope['query_string'].decode()
        self.query_string = query_string
        if query_string:
            self._params = parse_query_string(
                query_string,
                keep_blank=self.options.keep_blank_qs_values,
                csv=self.options.auto_parse_qs_csv,
            )

        else:
            self._params = {}

        # PERF(vytas): Fall back to class variable(s) when unset.
        # self._cached_access_route = None
        # self._cached_forwarded = None
        # self._cached_forwarded_prefix = None
        # self._cached_forwarded_uri = None
        # self._cached_prefix = None
        # self._cached_relative_uri = None
        # self._cached_uri = None

        if self.method == 'GET':
            # NOTE(vytas): We do not really expect the Content-Type to be
            #   non-ASCII, however we assume ISO-8859-1 here for maximum
            #   compatibility with WSGI.

            # PERF(kgriffs): Normally we expect no Content-Type header, so
            #   use this pattern which is a little bit faster than dict.get()
            if b'content-type' in req_headers:
                self.content_type = req_headers[b'content-type'].decode('latin1')
            else:
                self.content_type = None
        else:
            # PERF(kgriffs): This is the most performant pattern when we expect
            #   the key to be present most of the time.
            try:
                self.content_type = req_headers[b'content-type'].decode('latin1')
            except KeyError:
                self.content_type = None

        # =====================================================================
        # The request body stream is created lazily
        # =====================================================================

        # NOTE(kgriffs): The ASGI spec states that "you should not trigger
        #   on a connection opening alone". I take this to mean that the app
        #   should have the opportunity to respond with a 401, for example,
        #   without having to first read any of the body. This is accomplished
        #   in Falcon by only reading the first data event when the app attempts
        #   to read from req.stream for the first time, and in uvicorn
        #   (for example) by not confirming a 100 Continue request unless
        #   the app calls receive() to read the request body.

        # PERF(vytas): Fall back to class variable(s) when unset.
        # self._stream = None
        self._receive: AsgiReceive = receive
        self._first_event: Optional[AsgiEvent] = first_event

        # =====================================================================
        # Create a context object
        # =====================================================================

        self.context = self.context_type()

    # ------------------------------------------------------------------------
    # Properties
    #
    # Much of the logic from the ASGI Request class is duplicted in these
    # property implementations; however, to make the code more DRY we would
    # have to factor out the common logic, which would add overhead to these
    # properties and slow them down. They are simple enough that we should
    # be able to keep them in sync with the WSGI side without too much
    # trouble.
    # ------------------------------------------------------------------------

    auth: Optional[str] = asgi_helpers._header_property('Authorization')
    expect: Optional[str] = asgi_helpers._header_property('Expect')
    if_range: Optional[str] = asgi_helpers._header_property('If-Range')
    referer: Optional[str] = asgi_helpers._header_property('Referer')
    user_agent: Optional[str] = asgi_helpers._header_property('User-Agent')

    @property
    def accept(self) -> str:
        # NOTE(kgriffs): Per RFC, a missing accept header is
        # equivalent to '*/*'
        try:
            return self._asgi_headers[b'accept'].decode('latin1') or '*/*'
        except KeyError:
            return '*/*'

    @property
    def content_length(self) -> Optional[int]:
        try:
            value = self._asgi_headers[b'content-length']
        except KeyError:
            return None

        try:
            # PERF(vytas): int() also works with a bytestring argument.
            value_as_int = int(value)
        except ValueError:
            # PERF(vytas): Check for an empty value in the except clause,
            #   because we do not expect ASGI servers to inject any headers
            #   that the client did not provide.

            # NOTE(kgriffs): Normalize an empty value to behave as if
            # the header were not included; wsgiref, at least, inserts
            # an empty CONTENT_LENGTH value if the request does not
            # set the header. Gunicorn and uWSGI do not do this, but
            # others might if they are trying to match wsgiref's
            # behavior too closely.
            if not value:
                return None

            msg = 'The value of the header must be a number.'
            raise errors.HTTPInvalidHeader(msg, 'Content-Length')

        if value_as_int < 0:
            msg = 'The value of the header must be a positive number.'
            raise errors.HTTPInvalidHeader(msg, 'Content-Length')

        return value_as_int

    @property
    def stream(self) -> BoundedStream:  # type: ignore[override]
        """File-like input object for reading the body of the request, if any."""
        if self.is_websocket:
            raise errors.UnsupportedError(
                'ASGI does not support reading the WebSocket handshake request body.'
            )

        if not self._stream:
            self._stream = BoundedStream(
                self._receive,
                first_event=self._first_event,
                content_length=self.content_length,
            )

        return self._stream

    # NOTE(kgriffs): This is provided as an alias in order to ease migration
    #   from WSGI, but is not documented since we do not want people using
    #   it in greenfield ASGI apps.
    @property
    def bounded_stream(self) -> BoundedStream:  # type: ignore[override]
        """Alias to :attr:`~.stream`."""
        return self.stream

    @property
    def root_path(self) -> str:
        # PERF(kgriffs): try...except is faster than get() assuming that
        #   we normally expect the key to exist. Even though ASGI 3.0
        #   allows servers to omit the key when the value is an
        #   empty string, at least uvicorn still includes it explicitly in
        #   that case.
        try:
            return self.scope['root_path']
        except KeyError:
            pass

        return ''

    @property
    # NOTE(caselit): Deprecated long ago. Warns since 4.0.
    @deprecation.deprecated(
        'Use `root_path` instead. '
        '(This compatibility alias will be removed in Falcon 5.0.)',
        is_property=True,
    )
    def app(self) -> str:
        """Deprecated alias for :attr:`root_path`."""
        return self.root_path

    @property
    def scheme(self) -> str:
        """URL scheme used for the request.

        One of ``'http'``, ``'https'``, ``'ws'``, or ``'wss'``. Defaults to ``'http'``
        for the ``http`` scope, or ``'ws'`` for the ``websocket`` scope, when
        the ASGI server does not include the scheme in the connection scope.

        Note:
            If the request was proxied, the scheme may not
            match what was originally requested by the client.
            :attr:`forwarded_scheme` can be used, instead,
            to handle such cases.
        """
        # PERF(kgriffs): Use try...except because we normally expect the
        #   key to be present.
        try:
            return self.scope['scheme']
        except KeyError:
            pass

        return 'ws' if self.is_websocket else 'http'

    @property
    def forwarded_scheme(self) -> str:
        # PERF(kgriffs): Since the Forwarded header is still relatively
        # new, we expect X-Forwarded-Proto to be more common, so
        # try to avoid calling self.forwarded if we can, since it uses a
        # try...catch that will usually result in a relatively expensive
        # raised exception.
        if b'forwarded' in self._asgi_headers:
            forwarded = self.forwarded
            if forwarded:
                # Use first hop, fall back on own scheme
                scheme = forwarded[0].scheme or self.scheme
            else:
                scheme = self.scheme
        else:
            # PERF(kgriffs): This call should normally succeed, so
            # just go for it without wasting time checking it
            # first. Note also that the indexing operator is
            # slightly faster than using get().
            try:
                scheme = (
                    self._asgi_headers[b'x-forwarded-proto'].decode('latin1').lower()
                )
            except KeyError:
                scheme = self.scheme

        return scheme

    @property
    def host(self) -> str:
        """Host request header field, if present.

        If the Host header is missing, this attribute resolves to the ASGI server's
        listening host name or IP address.
        """
        try:
            # NOTE(kgriffs): Prefer the host header; the web server
            # isn't supposed to mess with it, so it should be what
            # the client actually sent.
            host_header = self._asgi_headers[b'host'].decode('latin1')
            host, __ = parse_host(host_header)
        except KeyError:
            host, __ = self._asgi_server

        return host

    @property
    def forwarded_host(self) -> str:
        # PERF(kgriffs): Since the Forwarded header is still relatively
        # new, we expect X-Forwarded-Host to be more common, so
        # try to avoid calling self.forwarded if we can, since it uses a
        # try...catch that will usually result in a relatively expensive
        # raised exception.
        if b'forwarded' in self._asgi_headers:
            forwarded = self.forwarded
            if forwarded:
                # Use first hop, fall back on self
                host = forwarded[0].host or self.netloc
            else:
                host = self.netloc
        else:
            # PERF(kgriffs): This call should normally succeed, assuming
            # that the caller is expecting a forwarded header, so
            # just go for it without wasting time checking it
            # first.
            try:
                host = self._asgi_headers[b'x-forwarded-host'].decode('latin1')
            except KeyError:
                host = self.netloc

        return host

    @property
    def access_route(self) -> List[str]:
        """IP address of the original client (if known), as
        well as any known addresses of proxies fronting the ASGI server.

        The following request headers are checked, in order of
        preference, to determine the addresses:

            - ``Forwarded``
            - ``X-Forwarded-For``
            - ``X-Real-IP``

        In addition, the value of the "client" field from the ASGI
        connection scope will be appended to the end of the list if
        not already included in one of the above headers. If the
        "client" field is not available, it will default to
        ``'127.0.0.1'``.

        Note:
            Per `RFC 7239`_, the access route may contain "unknown"
            and obfuscated identifiers, in addition to IPv4 and
            IPv6 addresses

            .. _RFC 7239: https://tools.ietf.org/html/rfc7239

        Warning:
            Headers can be forged by any client or proxy. Use this
            property with caution and validate all values before
            using them. Do not rely on the access route to authorize
            requests!
        """  # noqa: D205
        if self._cached_access_route is None:
            # PERF(kgriffs): 'client' is optional according to the ASGI spec
            #   but it will probably be present, hence the try...except.
            try:
                # NOTE(kgriffs): The ASGI spec states that this can be
                #   any iterable. So we need to read and cache it in
                #   case the iterable is forward-only. But that is
                #   effectively what we are doing since we only ever
                #   access this field when setting self._cached_access_route
                client, __ = self.scope['client']
            except KeyError:
                # NOTE(kgriffs): Default to localhost so that app logic does
                #   note have to special-case the handling of a missing
                #   client field in the connection scope. This should be
                #   a reasonable default, but we can change it later if
                #   that turns out not to be the case.
                client = '127.0.0.1'

            headers = self._asgi_headers

            if b'forwarded' in headers:
                self._cached_access_route = []
                for hop in self.forwarded or ():
                    if hop.src is not None:
                        host, __ = parse_host(hop.src)
                        self._cached_access_route.append(host)
            elif b'x-forwarded-for' in headers:
                addresses = headers[b'x-forwarded-for'].decode('latin1').split(',')
                self._cached_access_route = [ip.strip() for ip in addresses]
            elif b'x-real-ip' in headers:
                self._cached_access_route = [headers[b'x-real-ip'].decode('latin1')]

            if self._cached_access_route:
                if self._cached_access_route[-1] != client:
                    self._cached_access_route.append(client)
            else:
                self._cached_access_route = [client] if client else []

        return self._cached_access_route

    @property
    def remote_addr(self) -> str:
        """IP address of the closest known client or proxy to
        the ASGI server, or ``'127.0.0.1'`` if unknown.

        This property's value is equivalent to the last element of the
        :attr:`~.access_route` property.
        """  # noqa: D205
        route = self.access_route
        return route[-1]

    @property
    def port(self) -> int:
        try:
            host_header = self._asgi_headers[b'host'].decode('latin1')
            default_port = 443 if self._secure_scheme else 80
            __, port = parse_host(host_header, default_port=default_port)
        except KeyError:
            __, port = self._asgi_server

        return port

    @property
    def netloc(self) -> str:
        # PERF(kgriffs): try..except is faster than get() when we
        # expect the key to be present most of the time.
        try:
            netloc_value = self._asgi_headers[b'host'].decode('latin1')
        except KeyError:
            netloc_value, port = self._asgi_server

            if self._secure_scheme:
                if port != 443:
                    netloc_value = f'{netloc_value}:{port}'
            else:
                if port != 80:
                    netloc_value = f'{netloc_value}:{port}'

        return netloc_value

    async def get_media(self, default_when_empty: UnsetOr[Any] = _UNSET) -> Any:
        """Return a deserialized form of the request stream.

        The first time this method is called, the request stream will be
        deserialized using the Content-Type header as well as the media-type
        handlers configured via :class:`falcon.RequestOptions`. The result will
        be cached and returned in subsequent calls::

            deserialized_media = await req.get_media()

        If the matched media handler raises an error while attempting to
        deserialize the request body, the exception will propagate up
        to the caller.

        See also :ref:`media` for more information regarding media handling.

        Note:
            When ``get_media`` is called on a request with an empty body,
            Falcon will let the media handler try to deserialize the body
            and will return the value returned by the handler or propagate
            the exception raised by it. To instead return a different value
            in case of an exception by the handler, specify the argument
            ``default_when_empty``.

        Warning:
            This operation will consume the request stream the first time
            it's called and cache the results. Follow-up calls will just
            retrieve a cached version of the object.

        Args:
            default_when_empty: Fallback value to return when there is no body
                in the request and the media handler raises an error
                (like in the case of the default JSON media handler).
                By default, Falcon uses the value returned by the media handler
                or propagates the raised exception, if any.
                This value is not cached, and will be used only for the current
                call.

        Returns:
            media (object): The deserialized media representation.
        """

        if self._media is not _UNSET:
            return self._media
        if self._media_error is not None:
            if default_when_empty is not _UNSET and isinstance(
                self._media_error, errors.MediaNotFoundError
            ):
                return default_when_empty
            raise self._media_error

        handler, _, deserialize_sync = self.options.media_handlers._resolve(
            self.content_type, self.options.default_media_type
        )

        try:
            if deserialize_sync:
                self._media = deserialize_sync(await self.stream.read())
            else:
                self._media = await handler.deserialize_async(
                    self.stream, self.content_type, self.content_length
                )

        except errors.MediaNotFoundError as err:
            self._media_error = err
            if default_when_empty is not _UNSET:
                return default_when_empty
            raise
        except Exception as err:
            self._media_error = err
            raise
        finally:
            if handler.exhaust_stream:
                await self.stream.exhaust()

        return self._media

    media: Awaitable[Any] = cast(Awaitable[Any], property(get_media))
    """An awaitable property that acts as an alias for
    :meth:`~.get_media`. This can be used to ease the porting of
    a WSGI app to ASGI, although the ``await`` keyword must still be
    added when referencing the property::

        deserialized_media = await req.media
    """

    @property
    def if_match(self) -> Optional[List[Union[ETag, Literal['*']]]]:
        # TODO(kgriffs): It may make sense at some point to create a
        #   header property generator that DRY's up the memoization
        #   pattern for us.
        if self._cached_if_match is _UNSET:
            header_value = self._asgi_headers.get(b'if-match')
            if header_value:
                self._cached_if_match = helpers._parse_etags(
                    header_value.decode('latin1')
                )
            else:
                self._cached_if_match = None

        return self._cached_if_match

    @property
    def if_none_match(self) -> Optional[List[Union[ETag, Literal['*']]]]:
        if self._cached_if_none_match is _UNSET:
            header_value = self._asgi_headers.get(b'if-none-match')
            if header_value:
                self._cached_if_none_match = helpers._parse_etags(
                    header_value.decode('latin1')
                )
            else:
                self._cached_if_none_match = None

        return self._cached_if_none_match

    @property
    def headers(self) -> Mapping[str, str]:
        """Raw HTTP headers from the request with dash-separated
        names normalized to lowercase.

        Note:
            This property differs from the WSGI version of ``Request.headers``
            in that the latter returns *uppercase* names for historical
            reasons. Middleware, such as tracing and logging components, that
            need to be compatible with both WSGI and ASGI apps should
            use :attr:`headers_lower` instead.

        Warning:
            Parsing all the headers to create this dict is done the first
            time this attribute is accessed, and the returned object should
            be treated as read-only. Note that this parsing can be costly,
            so unless you need all the headers in this format, you should
            instead use the ``get_header()`` method or one of the
            convenience attributes to get a value for a specific header.
        """  # noqa: D205
        # NOTE(kgriffs: First time here will cache the dict so all we
        # have to do is clone it in the future.
        if self._cached_headers is None:
            self._cached_headers = {
                name.decode('latin1'): value.decode('latin1')
                for name, value in self._asgi_headers.items()
            }

        return self._cached_headers

    @property
    def headers_lower(self) -> Mapping[str, str]:
        """Alias for :attr:`headers` provided to expose a uniform way to
        get lowercased headers for both WSGI and ASGI apps.
        """  # noqa: D205
        return self.headers

    # ------------------------------------------------------------------------
    # Public Methods
    # ------------------------------------------------------------------------

    @overload
    def get_header(
        self, name: str, required: Literal[True], default: Optional[str] = ...
    ) -> str: ...

    @overload
    def get_header(self, name: str, required: bool = ..., *, default: str) -> str: ...

    @overload
    def get_header(
        self, name: str, required: bool = False, default: Optional[str] = ...
    ) -> Optional[str]: ...

    # PERF(kgriffs): Using kwarg cache, in lieu of @lru_cache on a helper method
    #   that is then called from get_header(), was benchmarked to be more
    #   efficient across CPython 3.6/3.8 (regardless of cythonization) and
    #   PyPy 3.6.
    def get_header(
        self,
        name: str,
        required: bool = False,
        default: Optional[str] = None,
        _name_cache: Dict[str, bytes] = {},
    ) -> Optional[str]:
        """Retrieve the raw string value for the given header.

        Args:
            name (str): Header name, case-insensitive (e.g., 'Content-Type')

        Keyword Args:
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning gracefully when the
                header is not found (default ``False``).
            default (any): Value to return if the header
                is not found (default ``None``).

        Returns:
            str: The value of the specified header if it exists, or
            the default value if the header is not found and is not
            required.

        Raises:
            HTTPBadRequest: The header was not found in the request, but
                it was required.

        """

        try:
            asgi_name = _name_cache[name]
        except KeyError:
            asgi_name = name.lower().encode('latin1')
            if len(_name_cache) < 64:  # Somewhat arbitrary ceiling to mitigate abuse
                _name_cache[name] = asgi_name

        # Use try..except to optimize for the header existing in most cases
        try:
            # Don't take the time to cache beforehand, using HTTP naming.
            # This will be faster, assuming that most headers are looked
            # up only once, and not all headers will be requested.
            return self._asgi_headers[asgi_name].decode('latin1')

        except KeyError:
            if not required:
                return default

            raise errors.HTTPMissingHeader(name)

    @overload
    def get_param(
        self,
        name: str,
        required: Literal[True],
        store: StoreArg = ...,
        default: Optional[str] = ...,
    ) -> str: ...

    @overload
    def get_param(
        self,
        name: str,
        required: bool = ...,
        store: StoreArg = ...,
        *,
        default: str,
    ) -> str: ...

    @overload
    def get_param(
        self,
        name: str,
        required: bool = False,
        store: StoreArg = None,
        default: Optional[str] = None,
    ) -> Optional[str]: ...

    def get_param(
        self,
        name: str,
        required: bool = False,
        store: StoreArg = None,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Return the raw value of a query string parameter as a string.

        Note:
            If an HTML form is POSTed to the API using the
            *application/x-www-form-urlencoded* media type, Falcon can
            automatically parse the parameters from the request body via
            :meth:`~falcon.asgi.Request.get_media`.

            See also: :ref:`access_urlencoded_form`

        Note:
            Similar to the way multiple keys in form data are handled, if a
            query parameter is included in the query string multiple times,
            only one of those values will be returned, and it is undefined which
            one. This caveat also applies when
            :attr:`~falcon.RequestOptions.auto_parse_qs_csv` is enabled and the
            given parameter is assigned to a comma-separated list of values
            (e.g., ``foo=a,b,c``).

            When multiple values are expected for a parameter,
            :meth:`~.get_param_as_list` can be used to retrieve all of
            them at once.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'sort').

        Keyword Args:
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found (default ``False``).
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is present.
            default (any): If the param is not found returns the
                given value instead of ``None``

        Returns:
            str: The value of the param as a string, or ``None`` if param is
            not found and is not required.

        Raises:
            HTTPBadRequest: A required param is missing from the request.
        """

        # TODO(kgriffs): It seems silly to have to do this, simply to provide
        #   the ASGI-specific docstring above. Is there a better way?

        return super().get_param(name, required=required, store=store, default=default)

    @property
    def env(self) -> NoReturn:  # type:ignore[override]
        """The env property is not available in ASGI. Use :attr:`~.store` instead."""
        raise AttributeError(
            'The env property is not available in ASGI. Use :attr:`~.store` instead'
        )

    def log_error(self, message: str) -> NoReturn:
        """Write a message to the server's log.

        Warning:
            Although this method is inherited from the WSGI Request class, it is
            not supported for ASGI apps. Please use the standard library logging
            framework instead.
        """

        # NOTE(kgriffs): Normally the Pythonic thing to do would be to simply
        #   set this method to None so that it can't even be called, but we
        #   raise an error here to help people who are porting from WSGI.
        raise NotImplementedError(
            "ASGI does not support writing to the server's log. "
            'Please use the standard library logging framework '
            'instead.'
        )

    # ------------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------------

    @property
    def _asgi_server(self) -> Tuple[str, int]:
        if not self._asgi_server_cached:
            try:
                # NOTE(kgriffs): Since the ASGI spec states that 'server'
                #   can be any old iterable, we have to be careful to only
                #   read it once and cache the result in case the
                #   iterator is forward-only (not likely, but better
                #   safe than sorry).
                self._asgi_server_cached = tuple(self.scope['server'])
            except (KeyError, TypeError):
                # NOTE(kgriffs): Not found, or was None
                default_port = 443 if self._secure_scheme else 80
                self._asgi_server_cached = ('localhost', default_port)

        return self._asgi_server_cached

    @property
    def _secure_scheme(self) -> bool:
        return self.scheme == 'https' or self.scheme == 'wss'
