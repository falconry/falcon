# Copyright 2019 by Kurt Griffiths
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
from falcon import request_helpers as helpers  # NOQA: Required by fixed up WSGI Request attrs
import falcon.asgi._request_helpers as asgi_helpers
from falcon.asgi.stream import BoundedStream
from falcon.constants import SINGLETON_HEADERS
from falcon.forwarded import _parse_forwarded_header  # NOQA: Req. by fixed up WSGI Request attrs
from falcon.forwarded import Forwarded  # NOQA
import falcon.request
from falcon.util.uri import parse_host, parse_query_string


__all__ = ['Request']


class Request(falcon.request.Request):
    """

            remote_addr(str): IP address of the closest known client or proxy to
                the WSGI server, or '127.0.0.1' if unknown.

                This property's value is equivalent to the last element of the
                :py:attr:`~.access_route` property.

            access_route(list): IP address of the original client (if known), as
                well as any known addresses of proxies fronting the WSGI server.

                The following request headers are checked, in order of
                preference, to determine the addresses:

                    - ``Forwarded``
                    - ``X-Forwarded-For``
                    - ``X-Real-IP``

                In addition, the value of the 'client' field from the ASGI
                connection scope will be appended to the end of the list if
                not already included in one of the above headers. If the
                'client' field is not available, it will default to
                '127.0.0.1'.

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

    """

    __slots__ = [
        '_asgi_headers',
        '_asgi_server_cached'
        '_receive',
        '_stream',
        'scope',
    ]

    async def read():
        return b''

    def __init__(self, scope, receive, options=None):

        # =====================================================================
        # Prepare headers
        # =====================================================================

        req_headers = {}
        for header_name, header_value in scope['headers']:
            # NOTE(kgriffs): According to ASGI 3.0, header names are always
            #   lowercased, and both name and value are byte strings. Although
            #   technically header names and values are restricted to US-ASCII
            #   we decode using the default 'utf-8' because it is a little
            #   faster than passing an encoding option.
            header_name = header_name.decode()
            header_value = header_value.decode()

            # NOTE(kgriffs): There are no standard request headers that
            #   allow multiple instances to appear in the request while also
            #   disallowing list syntax.
            if header_name not in req_headers or header_name in SINGLETON_HEADERS:
                req_headers[header_name] = header_value
            else:
                req_headers[header_name] += ',' + header_value

        self._asgi_headers = req_headers

        # =====================================================================
        #  Misc.
        # =====================================================================

        self._asgi_server_cached = None  # Lazy

        self.scope = scope
        self.options = options if options else falcon.request.RequestOptions()

        self._wsgierrors = None
        self.method = scope['method']

        self.uri_template = None
        self._media = None

        # TODO(kgriffs): ASGI does not specify whether 'path' may be empty,
        #   as was allowed for WSGI.
        path = scope['path'] or '/'

        if (self.options.strip_url_path_trailing_slash and
                len(path) != 1 and path.endswith('/')):
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

        self._cached_access_route = None
        self._cached_forwarded = None
        self._cached_forwarded_prefix = None
        self._cached_forwarded_uri = None
        self._cached_headers = req_headers
        self._cached_prefix = None
        self._cached_relative_uri = None
        self._cached_uri = None

        if self.method == 'GET':
            # PERF(kgriffs): Normally we expect no Content-Type header, so
            #   use this pattern which is a little bit faster than dict.get()
            if 'content-type' in req_headers:
                self.content_type = req_headers['content-type']
            else:
                self.content_type = None
        else:
            # PERF(kgriffs): This is the most performant pattern when we expect
            #   the key to be present most of the time.
            try:
                self.content_type = req_headers['content-type']
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

        self._stream = None
        self._receive = receive

        # =====================================================================
        # Create a context object
        # =====================================================================

        self.context = self.context_type()

    # ------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------

    auth = asgi_helpers.header_property('Authorization')
    expect = asgi_helpers.header_property('Expect')
    if_range = asgi_helpers.header_property('If-Range')
    referer = asgi_helpers.header_property('Referer')
    user_agent = asgi_helpers.header_property('User-Agent')

    accept = asgi_helpers.fixup_wsgi_references(falcon.request.Request.accept)
    content_length = asgi_helpers.fixup_wsgi_references(falcon.request.Request.content_length)
    forwarded = asgi_helpers.fixup_wsgi_references(falcon.request.Request.forwarded)
    if_match = asgi_helpers.fixup_wsgi_references(falcon.request.Request.if_match)
    if_none_match = asgi_helpers.fixup_wsgi_references(falcon.request.Request.if_none_match)
    range = asgi_helpers.fixup_wsgi_references(falcon.request.Request.range)
    range_unit = asgi_helpers.fixup_wsgi_references(falcon.request.Request.range_unit)

    @property
    def stream(self):
        if not self._stream:
            self._stream = BoundedStream(self._receive, self.content_length)

        return self._stream

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

        return 'http'

    @property
    def forwarded_scheme(self):
        # PERF(kgriffs): Since the Forwarded header is still relatively
        # new, we expect X-Forwarded-Proto to be more common, so
        # try to avoid calling self.forwarded if we can, since it uses a
        # try...catch that will usually result in a relatively expensive
        # raised exception.
        if 'forwarded' in self._asgi_headers:
            first_hop = self.forwarded[0]
            scheme = first_hop.scheme or self.scheme
        else:
            # PERF(kgriffs): This call should normally succeed, so
            # just go for it without wasting time checking it
            # first. Note also that the indexing operator is
            # slightly faster than using get().
            try:
                scheme = self._asgi_headers['x-forwarded-proto'].lower()
            except KeyError:
                scheme = self.scheme

        return scheme

    @property
    def prefix(self):
        if self._cached_prefix is None:
            self._cached_prefix = (
                self.scheme + '://' +
                self.netloc +
                self.app
            )

        return self._cached_prefix

    @property
    def host(self):
        try:
            # NOTE(kgriffs): Prefer the host header; the web server
            # isn't supposed to mess with it, so it should be what
            # the client actually sent.
            host_header = self._asgi_headers['host']
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
        if 'forwarded' in self._asgi_headers:
            first_hop = self.forwarded[0]
            host = first_hop.host or self.host
        else:
            # PERF(kgriffs): This call should normally succeed, assuming
            # that the caller is expecting a forwarded header, so
            # just go for it without wasting time checking it
            # first.
            try:
                host = self._asgi_headers['x-forwarded-host']
            except KeyError:
                host = self.host

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

            if 'forwarded' in headers:
                self._cached_access_route = []
                for hop in self.forwarded:
                    if hop.src is not None:
                        host, __ = parse_host(hop.src)
                        self._cached_access_route.append(host)
            elif 'x-forwarded-for' in headers:
                addresses = headers['x-forwarded-for'].split(',')
                self._cached_access_route = [ip.strip() for ip in addresses]
            elif 'x-real-ip' in headers:
                self._cached_access_route = [headers['x-real-ip']]

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
            host_header = self._asgi_headers['host']
            default_port = 80 if self.scheme == 'http' else 443
            __, port = parse_host(host_header, default_port=default_port)
        except KeyError:
            __, port = self._asgi_server

        return port

    @property
    def netloc(self):
        # PERF(kgriffs): try..except is faster than get() when we
        # expect the key to be present most of the time.
        try:
            netloc_value = self._asgi_headers['host']
        except KeyError:
            netloc_value, port = self._asgi_server

            if self.scheme == 'https':
                if port != 443:
                    netloc_value = f'{netloc_value}:{port}'
            else:
                if port != 80:
                    netloc_value = f'{netloc_value}:{port}'

        return netloc_value

    @property
    async def media(self):
        stream = self.stream

        if self._media is not None or stream.eof:
            return self._media

        content_type = self.content_type

        handler = self.options.media_handlers.find_by_media_type(
            content_type, self.options.default_media_type
        )

        try:
            self._media = await handler.deserialize_async(
                stream, content_type, self.content_length
            )
        finally:
            if not stream.eof:
                await stream.exhaust()

        return self._media

    # ------------------------------------------------------------------------
    # Public Methods
    # ------------------------------------------------------------------------

    def get_header(self, name, required=False, default=None):
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

        asgi_name = name.lower()

        # Use try..except to optimize for the header existing in most cases
        try:
            # Don't take the time to cache beforehand, using HTTP naming.
            # This will be faster, assuming that most headers are looked
            # up only once, and not all headers will be requested.
            return self._asgi_headers[asgi_name]

        except KeyError:
            if not required:
                return default

            raise errors.HTTPMissingHeader(name)

    # ASGI does not have anything equivalent to wsgi.errors
    log_error = None

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
                default_port = 80 if self.scheme == 'http' else 443
                self._asgi_server_cached = ('localhost', default_port)

        return self._asgi_server_cached

    async def _parse_form_urlencoded(self):
        if (
            self.content_type is not None and

            # PERF(kgriffs): Technically, we should spend a few more
            # cycles and parse the content type for real, but
            # this heuristic will work virtually all the time.
            'application/x-www-form-urlencoded' in self.content_type and

            # NOTE(kgriffs): Within HTTP, a payload for a GET or HEAD
            # request has no defined semantics, so we don't expect a
            # body in those cases. We would normally not expect a body
            # for OPTIONS either, but RFC 7231 does allow for it.
            self.method not in ('GET', 'HEAD')
        ):
            body = await self.stream.read()

            # NOTE(kgriffs): According to http://goo.gl/6rlcux the
            # body should be US-ASCII. Enforcing this also helps
            # catch malicious input.
            try:
                body = body.decode('ascii')
            except UnicodeDecodeError:
                body = None

            if body:
                extra_params = parse_query_string(
                    body,
                    keep_blank=self.options.keep_blank_qs_values,
                    csv=self.options.auto_parse_qs_csv,
                )

                self._params.update(extra_params)
