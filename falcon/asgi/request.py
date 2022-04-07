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

from falcon import errors
from falcon import request
from falcon import request_helpers as helpers
from falcon.constants import _UNSET
from falcon.constants import SINGLETON_HEADERS
from falcon.util.uri import parse_host
from falcon.util.uri import parse_query_string
from . import _request_helpers as asgi_helpers
from .stream import BoundedStream


__all__ = ['Request']

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

    Attributes:
        scope (dict): Reference to the ASGI HTTP connection scope passed in
            from the server (see also: `Connection Scope`_).
        context (object): Empty object to hold any data (in its attributes)
            about the request which is specific to your app (e.g. session
            object). Falcon itself will not interact with this attribute after
            it has been initialized.

            Note:
                The preferred way to pass request-specific data, when using the
                default context type, is to set attributes directly on the
                `context` object. For example::

                    req.context.role = 'trial'
                    req.context.user = 'guest'

        context_type (class): Class variable that determines the factory or
            type to use for initializing the `context` attribute. By default,
            the framework will instantiate bare objects (instances of the bare
            :class:`falcon.Context` class). However, you may override this
            behavior by creating a custom child class of
            ``falcon.asgi.Request``, and then passing that new class to
            `falcon.asgi.App()` by way of the latter's `request_type` parameter.

            Note:
                When overriding `context_type` with a factory function (as
                opposed to a class), the function is called like a method of
                the current ``Request`` instance. Therefore the first argument
                is the Request instance itself (i.e., `self`).

        scheme (str): URL scheme used for the request. One of ``'http'``,
            ``'https'``, ``'ws'``, or ``'wss'``. Defaults to ``'http'`` for
            the ``http`` scope, or ``'ws'`` for the ``websocket`` scope, when
            the ASGI server does not include the scheme in the connection
            scope.

            Note:
                If the request was proxied, the scheme may not
                match what was originally requested by the client.
                :py:attr:`forwarded_scheme` can be used, instead,
                to handle such cases.

        is_websocket (bool): Set to ``True`` IFF this request was made as part
            of a WebSocket handshake.

        forwarded_scheme (str): Original URL scheme requested by the
            user agent, if the request was proxied. Typical values are
            ``'http'`` or ``'https'``.

            The following request headers are checked, in order of
            preference, to determine the forwarded scheme:

                - ``Forwarded``
                - ``X-Forwarded-For``

            If none of these headers are available, or if the
            Forwarded header is available but does not contain a
            "proto" parameter in the first hop, the value of
            :attr:`scheme` is returned instead.

            (See also: RFC 7239, Section 1)

        method (str): HTTP method requested, uppercased (e.g.,
            ``'GET'``, ``'POST'``, etc.)
        host (str): Host request header field, if present. If the Host
            header is missing, this attribute resolves to the ASGI server's
            listening host name or IP address.
        forwarded_host (str): Original host request header as received
            by the first proxy in front of the application server.

            The following request headers are checked, in order of
            preference, to determine the forwarded scheme:

                - ``Forwarded``
                - ``X-Forwarded-Host``

            If none of the above headers are available, or if the
            Forwarded header is available but the "host"
            parameter is not included in the first hop, the value of
            :attr:`host` is returned instead.

            Note:
                Reverse proxies are often configured to set the Host
                header directly to the one that was originally
                requested by the user agent; in that case, using
                :attr:`host` is sufficient.

            (See also: RFC 7239, Section 4)

        port (int): Port used for the request. If the Host header is present
            in the request, but does not specify a port, the default one for the
            given schema is returned (80 for HTTP and 443 for HTTPS). If the
            request does not include a Host header, the listening port for the
            ASGI server is returned instead.
        netloc (str): Returns the "host:port" portion of the request
            URL. The port may be omitted if it is the default one for
            the URL's schema (80 for HTTP and 443 for HTTPS).
        subdomain (str): Leftmost (i.e., most specific) subdomain from the
            hostname. If only a single domain name is given, `subdomain`
            will be ``None``.

            Note:
                If the hostname in the request is an IP address, the value
                for `subdomain` is undefined.

        root_path (str): The initial portion of the request URI's path that
            corresponds to the application object, so that the
            application knows its virtual "location". This may be an
            empty string, if the application corresponds to the "root"
            of the server.

            (Corresponds to the "root_path" ASGI HTTP scope field.)

        uri (str): The fully-qualified URI for the request.
        url (str): Alias for :attr:`uri`.
        forwarded_uri (str): Original URI for proxied requests. Uses
            :attr:`forwarded_scheme` and :attr:`forwarded_host` in
            order to reconstruct the original URI requested by the user
            agent.
        relative_uri (str): The path and query string portion of the
            request URI, omitting the scheme and host.
        prefix (str): The prefix of the request URI, including scheme,
            host, and app :attr:`~.root_path` (if any).
        forwarded_prefix (str): The prefix of the original URI for
            proxied requests. Uses :attr:`forwarded_scheme` and
            :attr:`forwarded_host` in order to reconstruct the
            original URI.
        path (str): Path portion of the request URI (not including query
            string).

            Warning:
                If this attribute is to be used by the app for any upstream
                requests, any non URL-safe characters in the path must be URL
                encoded back before making the request.

            Note:
                ``req.path`` may be set to a new value by a
                ``process_request()`` middleware method in order to influence
                routing. If the original request path was URL encoded, it will
                be decoded before being returned by this attribute.

        query_string (str): Query string portion of the request URI, without
            the preceding '?' character.
        uri_template (str): The template for the route that was matched for
            this request. May be ``None`` if the request has not yet been
            routed, as would be the case for ``process_request()`` middleware
            methods. May also be ``None`` if your app uses a custom routing
            engine and the engine does not provide the URI template when
            resolving a route.
        remote_addr(str): IP address of the closest known client or proxy to
            the ASGI server, or ``'127.0.0.1'`` if unknown.

            This property's value is equivalent to the last element of the
            :py:attr:`~.access_route` property.

        access_route(list): IP address of the original client (if known), as
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

        forwarded (list): Value of the Forwarded header, as a parsed list
            of :class:`falcon.Forwarded` objects, or ``None`` if the header
            is missing. If the header value is malformed, Falcon will
            make a best effort to parse what it can.

            (See also: RFC 7239, Section 4)
        date (datetime): Value of the Date header, converted to a
            ``datetime`` instance. The header value is assumed to
            conform to RFC 1123.
        auth (str): Value of the Authorization header, or ``None`` if the
            header is missing.
        user_agent (str): Value of the User-Agent header, or ``None`` if the
            header is missing.
        referer (str): Value of the Referer header, or ``None`` if
            the header is missing.
        accept (str): Value of the Accept header, or ``'*/*'`` if the header is
            missing.
        client_accepts_json (bool): ``True`` if the Accept header indicates
            that the client is willing to receive JSON, otherwise ``False``.
        client_accepts_msgpack (bool): ``True`` if the Accept header indicates
            that the client is willing to receive MessagePack, otherwise
            ``False``.
        client_accepts_xml (bool): ``True`` if the Accept header indicates that
            the client is willing to receive XML, otherwise ``False``.
        cookies (dict):
            A dict of name/value cookie pairs. The returned object should be
            treated as read-only to avoid unintended side-effects.
            If a cookie appears more than once in the request, only the first
            value encountered will be made available here.

            See also: :meth:`~falcon.asgi.Request.get_cookie_values`
        content_type (str): Value of the Content-Type header, or ``None`` if
            the header is missing.
        content_length (int): Value of the Content-Length header converted
            to an ``int``, or ``None`` if the header is missing.
        stream (falcon.asgi.BoundedStream): File-like input object for reading
            the body of the request, if any.

            See also: :class:`falcon.asgi.BoundedStream`
        media (object): An awaitable property that acts as an alias for
            :meth:`~.get_media`. This can be used to ease the porting of
            a WSGI app to ASGI, although the ``await`` keyword must still be
            added when referencing the property::

                deserialized_media = await req.media

        expect (str): Value of the Expect header, or ``None`` if the
            header is missing.
        range (tuple of int): A 2-member ``tuple`` parsed from the value of the
            Range header.

            The two members correspond to the first and last byte
            positions of the requested resource, inclusive. Negative
            indices indicate offset from the end of the resource,
            where -1 is the last byte, -2 is the second-to-last byte,
            and so forth.

            Only continuous ranges are supported (e.g., "bytes=0-0,-1" would
            result in an HTTPBadRequest exception when the attribute is
            accessed.)
        range_unit (str): Unit of the range parsed from the value of the
            Range header, or ``None`` if the header is missing
        if_match (list): Value of the If-Match header, as a parsed list of
            :class:`falcon.ETag` objects or ``None`` if the header is missing
            or its value is blank.

            This property provides a list of all ``entity-tags`` in the
            header, both strong and weak, in the same order as listed in
            the header.

            (See also: RFC 7232, Section 3.1)

        if_none_match (list): Value of the If-None-Match header, as a parsed
            list of :class:`falcon.ETag` objects or ``None`` if the header is
            missing or its value is blank.

            This property provides a list of all ``entity-tags`` in the
            header, both strong and weak, in the same order as listed in
            the header.

            (See also: RFC 7232, Section 3.2)

        if_modified_since (datetime): Value of the If-Modified-Since header,
            or ``None`` if the header is missing.
        if_unmodified_since (datetime): Value of the If-Unmodified-Since
            header, or ``None`` if the header is missing.
        if_range (str): Value of the If-Range header, or ``None`` if the
            header is missing.

        headers (dict): Raw HTTP headers from the request with
            canonical dash-separated names. Parsing all the headers
            to create this dict is done the first time this attribute
            is accessed, and the returned object should be treated as
            read-only. Note that this parsing can be costly, so unless you
            need all the headers in this format, you should instead use the
            ``get_header()`` method or one of the convenience attributes
            to get a value for a specific header.

        params (dict): The mapping of request query parameter names to their
            values.  Where the parameter appears multiple times in the query
            string, the value mapped to that parameter key will be a list of
            all the values in the order seen.

        options (falcon.request.RequestOptions): Set of global options passed
            in from the App handler.

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
    _asgi_server_cached = None
    _cached_access_route = None
    _cached_forwarded = None
    _cached_forwarded_prefix = None
    _cached_forwarded_uri = None
    _cached_headers = None
    _cached_prefix = None
    _cached_relative_uri = None
    _cached_uri = None
    _media = _UNSET
    _media_error = None
    _stream = None
    _wsgi_errors = None

    def __init__(self, scope, receive, first_event=None, options=None):

        # =====================================================================
        # Prepare headers
        # =====================================================================

        req_headers = {}
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

        self._asgi_headers = req_headers
        # PERF(vytas): Fall back to class variable(s) when unset.
        # self._cached_headers = None

        # =====================================================================
        #  Misc.
        # =====================================================================

        # PERF(vytas): Fall back to class variable(s) when unset.
        # self._asgi_server_cached = None  # Lazy
        self.scope = scope
        self.is_websocket = scope['type'] == 'websocket'

        self.options = options if options else request.RequestOptions()

        # PERF(vytas): Fall back to class variable(s) when unset.
        # self._wsgierrors = None
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
        self._receive = receive
        self._first_event = first_event

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

    auth = asgi_helpers.header_property('Authorization')
    expect = asgi_helpers.header_property('Expect')
    if_range = asgi_helpers.header_property('If-Range')
    referer = asgi_helpers.header_property('Referer')
    user_agent = asgi_helpers.header_property('User-Agent')

    @property
    def accept(self):
        # NOTE(kgriffs): Per RFC, a missing accept header is
        # equivalent to '*/*'
        try:
            return self._asgi_headers[b'accept'].decode('latin1') or '*/*'
        except KeyError:
            return '*/*'

    @property
    def content_length(self):
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
    def stream(self):
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
    bounded_stream = stream

    @property
    def root_path(self):
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

    app = root_path

    @property
    def scheme(self):
        # PERF(kgriffs): Use try...except because we normally expect the
        #   key to be present.
        try:
            return self.scope['scheme']
        except KeyError:
            pass

        return 'ws' if self.is_websocket else 'http'

    @property
    def forwarded_scheme(self):
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
    def host(self):
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
    def forwarded_host(self):
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
    def access_route(self):
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
                for hop in self.forwarded:
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
    def remote_addr(self):
        route = self.access_route
        return route[-1]

    @property
    def port(self):
        try:
            host_header = self._asgi_headers[b'host'].decode('latin1')
            default_port = 443 if self._secure_scheme else 80
            __, port = parse_host(host_header, default_port=default_port)
        except KeyError:
            __, port = self._asgi_server

        return port

    @property
    def netloc(self):
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

    async def get_media(self, default_when_empty=_UNSET):
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

    media = property(get_media)

    @property
    def if_match(self):
        # TODO(kgriffs): It may make sense at some point to create a
        #   header property generator that DRY's up the memoization
        #   pattern for us.
        # PERF(kgriffs): It probably isn't worth it to set
        #   self._cached_if_match to a special type/object to distinguish
        #   between the variable being unset and the header not being
        #   present in the request. The reason is that if the app
        #   gets a None back on the first reference to property, it
        #   probably isn't going to access the property again (TBD).
        if self._cached_if_match is None:
            header_value = self._asgi_headers.get(b'if-match')
            if header_value:
                self._cached_if_match = helpers._parse_etags(
                    header_value.decode('latin1')
                )

        return self._cached_if_match

    @property
    def if_none_match(self):
        if self._cached_if_none_match is None:
            header_value = self._asgi_headers.get(b'if-none-match')
            if header_value:
                self._cached_if_none_match = helpers._parse_etags(
                    header_value.decode('latin1')
                )

        return self._cached_if_none_match

    @property
    def headers(self):
        # NOTE(kgriffs: First time here will cache the dict so all we
        # have to do is clone it in the future.
        if self._cached_headers is None:
            self._cached_headers = {
                name.decode('latin1'): value.decode('latin1')
                for name, value in self._asgi_headers.items()
            }

        return self._cached_headers

    # ------------------------------------------------------------------------
    # Public Methods
    # ------------------------------------------------------------------------

    # PERF(kgriffs): Using kwarg cache, in lieu of @lru_cache on a helper method
    #   that is then called from get_header(), was benchmarked to be more
    #   efficient across CPython 3.6/3.8 (regardless of cythonization) and
    #   PyPy 3.6.
    def get_header(self, name, required=False, default=None, _name_cache={}):
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

    def get_param(self, name, required=False, store=None, default=None):
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

    def log_error(self, message):
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
    def _asgi_server(self):
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
    def _secure_scheme(self):
        return self.scheme == 'https' or self.scheme == 'wss'
