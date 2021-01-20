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

"""Request class."""

from datetime import datetime
from io import BytesIO
from uuid import UUID

from falcon import errors
from falcon import request_helpers as helpers
from falcon import util
from falcon.constants import _UNSET
from falcon.constants import DEFAULT_MEDIA_TYPE
from falcon.constants import MEDIA_JSON
from falcon.forwarded import _parse_forwarded_header
# TODO: remove import in falcon 4
from falcon.forwarded import Forwarded  # NOQA
from falcon.media import Handlers
from falcon.media.json import _DEFAULT_JSON_HANDLER
from falcon.stream import BoundedStream
from falcon.util import structures
from falcon.util.misc import isascii
from falcon.util.uri import parse_host
from falcon.util.uri import parse_query_string
from falcon.vendor import mimeparse

DEFAULT_ERROR_LOG_FORMAT = ('{0:%Y-%m-%d %H:%M:%S} [FALCON] [ERROR]'
                            ' {1} {2}{3} => ')

TRUE_STRINGS = frozenset(['true', 'True', 't', 'yes', 'y', '1', 'on'])
FALSE_STRINGS = frozenset(['false', 'False', 'f', 'no', 'n', '0', 'off'])
WSGI_CONTENT_HEADERS = frozenset(['CONTENT_TYPE', 'CONTENT_LENGTH'])

# PERF(kgriffs): Avoid an extra namespace lookup when using these functions
strptime = datetime.strptime
now = datetime.now


class Request:
    """Represents a client's HTTP request.

    Note:
        `Request` is not meant to be instantiated directly by responders.

    Args:
        env (dict): A WSGI environment dict passed in from the server. See
            also PEP-3333.

    Keyword Arguments:
        options (dict): Set of global options passed from the App handler.

    Attributes:
        env (dict): Reference to the WSGI environ ``dict`` passed in from the
            server. (See also PEP-3333.)
        context (object): Empty object to hold any data (in its attributes)
            about the request which is specific to your app (e.g. session
            object). Falcon itself will not interact with this attribute after
            it has been initialized.

            Note:
                **New in 2.0:** The default `context_type` (see below) was
                changed from :class:`dict` to a bare class; the preferred way to
                pass request-specific data is now to set attributes directly on
                the `context` object. For example::

                    req.context.role = 'trial'
                    req.context.user = 'guest'

        context_type (class): Class variable that determines the factory or
            type to use for initializing the `context` attribute. By default,
            the framework will instantiate bare objects (instances of the bare
            :class:`falcon.Context` class). However, you may override this
            behavior by creating a custom child class of ``falcon.Request``,
            and then passing that new class to `falcon.App()` by way of the
            latter's `request_type` parameter.

            Note:
                When overriding `context_type` with a factory function (as
                opposed to a class), the function is called like a method of
                the current Request instance. Therefore the first argument is
                the Request instance itself (self).
        scheme (str): URL scheme used for the request. Either 'http' or
            'https'.

            Note:
                If the request was proxied, the scheme may not
                match what was originally requested by the client.
                :py:attr:`forwarded_scheme` can be used, instead,
                to handle such cases.

        forwarded_scheme (str): Original URL scheme requested by the
            user agent, if the request was proxied. Typical values are
            'http' or 'https'.

            The following request headers are checked, in order of
            preference, to determine the forwarded scheme:

                - ``Forwarded``
                - ``X-Forwarded-For``

            If none of these headers are available, or if the
            Forwarded header is available but does not contain a
            "proto" parameter in the first hop, the value of
            :attr:`scheme` is returned instead.

            (See also: RFC 7239, Section 1)

        method (str): HTTP method requested (e.g., 'GET', 'POST', etc.)
        host (str): Host request header field
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
            WSGI server is returned instead.
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

            (Corresponds to the "SCRIPT_NAME" environ variable defined
            by PEP-3333.)
        app (str): Deprecated alias for :attr:`root_path`.
        uri (str): The fully-qualified URI for the request.
        url (str): Alias for :attr:`uri`.
        forwarded_uri (str): Original URI for proxied requests. Uses
            :attr:`forwarded_scheme` and :attr:`forwarded_host` in
            order to reconstruct the original URI requested by the user
            agent.
        relative_uri (str): The path and query string portion of the
            request URI, omitting the scheme and host.
        prefix (str): The prefix of the request URI, including scheme,
            host, and WSGI app (if any).
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
        remote_addr(str): IP address of the closest client or proxy to
            the WSGI server.

            This property is determined by the value of ``REMOTE_ADDR``
            in the WSGI environment dict. Since this address is not
            derived from an HTTP header, clients and proxies can not
            forge it.

            Note:
                If your application is behind one or more reverse
                proxies, you can use :py:attr:`~.access_route`
                to retrieve the real IP address of the client.
        access_route(list): IP address of the original client, as well
            as any known addresses of proxies fronting the WSGI server.

            The following request headers are checked, in order of
            preference, to determine the addresses:

                - ``Forwarded``
                - ``X-Forwarded-For``
                - ``X-Real-IP``

            If none of these headers are available, the value of
            :py:attr:`~.remote_addr` is used instead.

            Note:
                Per `RFC 7239`_, the access route may contain "unknown"
                and obfuscated identifiers, in addition to IPv4 and
                IPv6 addresses

                .. _RFC 7239: https://tools.ietf.org/html/rfc7239

            Warning:
                Headers can be forged by any client or proxy. Use this
                property with caution and validate all values before
                using them. Do not rely on the access route to authorize
                requests.

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

            See also: :meth:`~falcon.Request.get_cookie_values`
        content_type (str): Value of the Content-Type header, or ``None`` if
            the header is missing.
        content_length (int): Value of the Content-Length header converted
            to an ``int``, or ``None`` if the header is missing.
        stream: File-like input object for reading the body of the
            request, if any. This object provides direct access to the
            server's data stream and is non-seekable. In order to
            avoid unintended side effects, and to provide maximum
            flexibility to the application, Falcon itself does not
            buffer or spool the data in any way.

            Since this object is provided by the WSGI
            server itself, rather than by Falcon, it may behave
            differently depending on how you host your app. For example,
            attempting to read more bytes than are expected (as
            determined by the Content-Length header) may or may not
            block indefinitely. It's a good idea to test your WSGI
            server to find out how it behaves.

            This can be particulary problematic when a request body is
            expected, but none is given. In this case, the following
            call blocks under certain WSGI servers::

                # Blocks if Content-Length is 0
                data = req.stream.read()

            The workaround is fairly straightforward, if verbose::

                # If Content-Length happens to be 0, or the header is
                # missing altogether, this will not block.
                data = req.stream.read(req.content_length or 0)

            Alternatively, when passing the stream directly to a
            consumer, it may be necessary to branch off the
            value of the Content-Length header::

                if req.content_length:
                    doc = json.load(req.stream)

            For a slight performance cost, you may instead wish to use
            :py:attr:`bounded_stream`, which wraps the native WSGI
            input object to normalize its behavior.

            Note:
                If an HTML form is POSTed to the API using the
                *application/x-www-form-urlencoded* media type, and
                the :py:attr:`~.RequestOptions.auto_parse_form_urlencoded`
                option is set, the framework
                will consume `stream` in order to parse the parameters
                and merge them into the query string parameters. In this
                case, the stream will be left at EOF.

        bounded_stream: File-like wrapper around `stream` to normalize
            certain differences between the native input objects
            employed by different WSGI servers. In particular,
            `bounded_stream` is aware of the expected Content-Length of
            the body, and will never block on out-of-bounds reads,
            assuming the client does not stall while transmitting the
            data to the server.

            For example, the following will not block when
            Content-Length is 0 or the header is missing altogether::

                data = req.bounded_stream.read()

            This is also safe::

                doc = json.load(req.bounded_stream)

        media (object): Property that acts as an alias for
            :meth:`~.get_media`. This alias provides backwards-compatibility
            for apps that were built for versions of the framework prior to
            3.0::

                # Equivalent to: deserialized_media = req.get_media()
                deserialized_media = req.media

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

        options (dict): Set of global options passed from the App handler.
    """

    __slots__ = (
        '__dict__',
        '_bounded_stream',
        '_cached_access_route',
        '_cached_forwarded',
        '_cached_forwarded_prefix',
        '_cached_forwarded_uri',
        '_cached_headers',
        '_cached_prefix',
        '_cached_relative_uri',
        '_cached_uri',
        '_params',
        '_wsgierrors',
        'content_type',
        'context',
        'env',
        'method',
        'options',
        'path',
        'query_string',
        'stream',
        'uri_template',
        '_media',
        '_media_error',
        'is_websocket',
    )

    _cookies = None
    _cookies_collapsed = None
    _cached_if_match = None
    _cached_if_none_match = None

    # Child classes may override this
    context_type = structures.Context

    _wsgi_input_type_known = False

    def __init__(self, env, options=None):
        self.is_websocket = False

        self.env = env
        self.options = options if options else RequestOptions()

        self._wsgierrors = env['wsgi.errors']
        self.method = env['REQUEST_METHOD']

        self.uri_template = None
        self._media = _UNSET
        self._media_error = None

        # NOTE(kgriffs): PEP 3333 specifies that PATH_INFO may be the
        # empty string, so normalize it in that case.
        path = env['PATH_INFO'] or '/'

        # PEP 3333 specifies that the PATH_INFO variable is always
        # "bytes tunneled as latin-1" and must be encoded back.
        #
        # NOTE(kgriffs): The decoded path may contain UTF-8 characters.
        # But according to the WSGI spec, no strings can contain chars
        # outside ISO-8859-1. Therefore, to reconcile the URI
        # encoding standard that allows UTF-8 with the WSGI spec
        # that does not, WSGI servers tunnel the string via
        # ISO-8859-1, e.g.:
        #
        #   tunnelled_path = path.encode('utf-8').decode('iso-8859-1')

        # perf(vytas): Only decode the tunnelled path in case it is not ASCII.
        #   For ASCII-strings, the below decoding chain is a no-op.
        if not isascii(path):
            path = path.encode('iso-8859-1').decode('utf-8', 'replace')

        if (self.options.strip_url_path_trailing_slash and
                len(path) != 1 and path.endswith('/')):
            self.path = path[:-1]
        else:
            self.path = path

        # PERF(ueg1990): try/catch cheaper and faster (and more Pythonic)
        try:
            self.query_string = env['QUERY_STRING']
        except KeyError:
            self.query_string = ''
            self._params = {}
        else:
            if self.query_string:
                self._params = parse_query_string(
                    self.query_string,
                    keep_blank=self.options.keep_blank_qs_values,
                    csv=self.options.auto_parse_qs_csv,
                )

            else:
                self._params = {}

        self._cached_access_route = None
        self._cached_forwarded = None
        self._cached_forwarded_prefix = None
        self._cached_forwarded_uri = None
        self._cached_headers = None
        self._cached_prefix = None
        self._cached_relative_uri = None
        self._cached_uri = None

        try:
            self.content_type = self.env['CONTENT_TYPE']
        except KeyError:
            self.content_type = None

        self.stream = env['wsgi.input']
        self._bounded_stream = None  # Lazy wrapping

        # PERF(kgriffs): Technically, we should spend a few more
        # cycles and parse the content type for real, but
        # this heuristic will work virtually all the time.
        if (
            self.options.auto_parse_form_urlencoded and
            self.content_type is not None and
            'application/x-www-form-urlencoded' in self.content_type and

            # NOTE(kgriffs): Within HTTP, a payload for a GET or HEAD
            # request has no defined semantics, so we don't expect a
            # body in those cases. We would normally not expect a body
            # for OPTIONS either, but RFC 7231 does allow for it.
            self.method not in ('GET', 'HEAD')
        ):
            self._parse_form_urlencoded()

        self.context = self.context_type()

    def __repr__(self):
        return '<%s: %s %r>' % (self.__class__.__name__, self.method, self.url)

    # ------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------

    user_agent = helpers.header_property('HTTP_USER_AGENT')
    auth = helpers.header_property('HTTP_AUTHORIZATION')

    expect = helpers.header_property('HTTP_EXPECT')

    if_range = helpers.header_property('HTTP_IF_RANGE')

    referer = helpers.header_property('HTTP_REFERER')

    @property
    def forwarded(self):
        # PERF(kgriffs): We could DRY up this memoization pattern using
        # a decorator, but that would incur additional overhead without
        # resorting to some trickery to rewrite the body of the method
        # itself (vs. simply wrapping it with some memoization logic).
        # At some point we might look into this but I don't think
        # it's worth it right now.
        if self._cached_forwarded is None:
            forwarded = self.get_header('Forwarded')
            if forwarded is None:
                return None

            self._cached_forwarded = _parse_forwarded_header(forwarded)

        return self._cached_forwarded

    @property
    def client_accepts_json(self):
        return self.client_accepts('application/json')

    @property
    def client_accepts_msgpack(self):
        return (self.client_accepts('application/x-msgpack') or
                self.client_accepts('application/msgpack'))

    @property
    def client_accepts_xml(self):
        return self.client_accepts('application/xml')

    @property
    def accept(self):
        # NOTE(kgriffs): Per RFC, a missing accept header is
        # equivalent to '*/*'
        try:
            return self.env['HTTP_ACCEPT'] or '*/*'
        except KeyError:
            return '*/*'

    @property
    def content_length(self):
        try:
            value = self.env['CONTENT_LENGTH']
        except KeyError:
            return None

        # NOTE(kgriffs): Normalize an empty value to behave as if
        # the header were not included; wsgiref, at least, inserts
        # an empty CONTENT_LENGTH value if the request does not
        # set the header. Gunicorn and uWSGI do not do this, but
        # others might if they are trying to match wsgiref's
        # behavior too closely.
        if not value:
            return None

        try:
            value_as_int = int(value)
        except ValueError:
            msg = 'The value of the header must be a number.'
            raise errors.HTTPInvalidHeader(msg, 'Content-Length')

        if value_as_int < 0:
            msg = 'The value of the header must be a positive number.'
            raise errors.HTTPInvalidHeader(msg, 'Content-Length')

        return value_as_int

    @property
    def bounded_stream(self):
        if self._bounded_stream is None:
            self._bounded_stream = self._get_wrapped_wsgi_input()

        return self._bounded_stream

    @property
    def date(self):
        return self.get_header_as_datetime('Date')

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
            header_value = self.env.get('HTTP_IF_MATCH')
            if header_value:
                self._cached_if_match = helpers._parse_etags(header_value)

        return self._cached_if_match

    @property
    def if_none_match(self):
        if self._cached_if_none_match is None:
            header_value = self.env.get('HTTP_IF_NONE_MATCH')
            if header_value:
                self._cached_if_none_match = helpers._parse_etags(header_value)

        return self._cached_if_none_match

    @property
    def if_modified_since(self):
        return self.get_header_as_datetime('If-Modified-Since')

    @property
    def if_unmodified_since(self):
        return self.get_header_as_datetime('If-Unmodified-Since')

    @property
    def range(self):
        value = self.get_header('Range')
        if value is None:
            return None

        if '=' in value:
            unit, sep, req_range = value.partition('=')
        else:
            msg = "The value must be prefixed with a range unit, e.g. 'bytes='"
            raise errors.HTTPInvalidHeader(msg, 'Range')

        if ',' in req_range:
            msg = 'The value must be a continuous range.'
            raise errors.HTTPInvalidHeader(msg, 'Range')

        try:
            first, sep, last = req_range.partition('-')

            if not sep:
                raise ValueError()

            if first:
                return (int(first), int(last or -1))
            elif last:
                return (-int(last), -1)
            else:
                msg = 'The range offsets are missing.'
                raise errors.HTTPInvalidHeader(msg, 'Range')

        except ValueError:
            href = 'http://goo.gl/zZ6Ey'
            href_text = 'HTTP/1.1 Range Requests'
            msg = 'It must be a range formatted according to RFC 7233.'
            raise errors.HTTPInvalidHeader(msg, 'Range', href=href,
                                           href_text=href_text)

    @property
    def range_unit(self):
        value = self.get_header('Range')
        if value is None:
            return None

        if value and '=' in value:
            unit, sep, req_range = value.partition('=')
            return unit
        else:
            msg = "The value must be prefixed with a range unit, e.g. 'bytes='"
            raise errors.HTTPInvalidHeader(msg, 'Range')

    @property
    def root_path(self):
        # PERF(kgriffs): try..except is faster than get() assuming that
        # we normally expect the key to exist. Even though PEP-3333
        # allows WSGI servers to omit the key when the value is an
        # empty string, uwsgi, gunicorn, waitress, and wsgiref all
        # include it even in that case.
        try:
            return self.env['SCRIPT_NAME']
        except KeyError:
            return ''

    app = root_path

    @property
    def scheme(self):
        return self.env['wsgi.url_scheme']

    @property
    def forwarded_scheme(self):
        # PERF(kgriffs): Since the Forwarded header is still relatively
        # new, we expect X-Forwarded-Proto to be more common, so
        # try to avoid calling self.forwarded if we can, since it uses a
        # try...catch that will usually result in a relatively expensive
        # raised exception.
        if 'HTTP_FORWARDED' in self.env:
            first_hop = self.forwarded[0]
            scheme = first_hop.scheme or self.scheme
        else:
            # PERF(kgriffs): This call should normally succeed, so
            # just go for it without wasting time checking it
            # first. Note also that the indexing operator is
            # slightly faster than using get().
            try:
                scheme = self.env['HTTP_X_FORWARDED_PROTO'].lower()
            except KeyError:
                scheme = self.env['wsgi.url_scheme']

        return scheme

    @property
    def uri(self):
        if self._cached_uri is None:
            # PERF: For small numbers of items, '+' is faster
            # than ''.join(...). Concatenation is also generally
            # faster than formatting.
            value = (self.scheme + '://' +
                     self.netloc +
                     self.relative_uri)

            self._cached_uri = value

        return self._cached_uri

    url = uri

    @property
    def forwarded_uri(self):
        if self._cached_forwarded_uri is None:
            # PERF: For small numbers of items, '+' is faster
            # than ''.join(...). Concatenation is also generally
            # faster than formatting.
            value = (self.forwarded_scheme + '://' +
                     self.forwarded_host +
                     self.relative_uri)

            self._cached_forwarded_uri = value

        return self._cached_forwarded_uri

    @property
    def relative_uri(self):
        if self._cached_relative_uri is None:
            if self.query_string:
                self._cached_relative_uri = (self.app + self.path + '?' +
                                             self.query_string)
            else:
                self._cached_relative_uri = self.app + self.path

        return self._cached_relative_uri

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
    def forwarded_prefix(self):
        if self._cached_forwarded_prefix is None:
            self._cached_forwarded_prefix = (
                self.forwarded_scheme + '://' +
                self.forwarded_host +
                self.app
            )

        return self._cached_forwarded_prefix

    @property
    def host(self):
        try:
            # NOTE(kgriffs): Prefer the host header; the web server
            # isn't supposed to mess with it, so it should be what
            # the client actually sent.
            host_header = self.env['HTTP_HOST']
            host, port = parse_host(host_header)
        except KeyError:
            # PERF(kgriffs): According to PEP-3333, this header
            # will always be present.
            host = self.env['SERVER_NAME']

        return host

    @property
    def forwarded_host(self):
        # PERF(kgriffs): Since the Forwarded header is still relatively
        # new, we expect X-Forwarded-Host to be more common, so
        # try to avoid calling self.forwarded if we can, since it uses a
        # try...catch that will usually result in a relatively expensive
        # raised exception.
        if 'HTTP_FORWARDED' in self.env:
            first_hop = self.forwarded[0]
            host = first_hop.host or self.netloc
        else:
            # PERF(kgriffs): This call should normally succeed, assuming
            # that the caller is expecting a forwarded header, so
            # just go for it without wasting time checking it
            # first.
            try:
                host = self.env['HTTP_X_FORWARDED_HOST']
            except KeyError:
                host = self.netloc

        return host

    @property
    def subdomain(self):
        # PERF(kgriffs): .partition is slightly faster than .split
        subdomain, sep, remainder = self.host.partition('.')
        return subdomain if sep else None

    @property
    def headers(self):
        # NOTE(kgriffs: First time here will cache the dict so all we
        # have to do is clone it in the future.
        if self._cached_headers is None:
            headers = self._cached_headers = {}

            env = self.env
            for name, value in env.items():
                if name.startswith('HTTP_'):
                    # NOTE(kgriffs): Don't take the time to fix the case
                    # since headers are supposed to be case-insensitive
                    # anyway.
                    headers[name[5:].replace('_', '-')] = value

                elif name in WSGI_CONTENT_HEADERS:
                    headers[name.replace('_', '-')] = value

        return self._cached_headers

    @property
    def params(self):
        return self._params

    @property
    def cookies(self):
        if self._cookies_collapsed is None:
            if self._cookies is None:
                header_value = self.get_header('Cookie')
                if header_value:
                    self._cookies = helpers.parse_cookie_header(header_value)
                else:
                    self._cookies = {}

            self._cookies_collapsed = {n: v[0] for n, v in self._cookies.items()}

        return self._cookies_collapsed

    @property
    def access_route(self):
        if self._cached_access_route is None:
            # NOTE(kgriffs): Try different headers in order of
            # preference; if none are found, fall back to REMOTE_ADDR.
            #
            # If one of these headers is present, but its value is
            # malformed such that we end up with an empty list, or
            # a non-empty list containing malformed values, go ahead
            # and return the results as-is. The alternative would be
            # to fall back to another header or to REMOTE_ADDR, but
            # that only masks the problem; the operator needs to be
            # aware that an upstream proxy is malfunctioning.

            if 'HTTP_FORWARDED' in self.env:
                self._cached_access_route = []
                for hop in self.forwarded:
                    if hop.src is not None:
                        host, __ = parse_host(hop.src)
                        self._cached_access_route.append(host)
            elif 'HTTP_X_FORWARDED_FOR' in self.env:
                addresses = self.env['HTTP_X_FORWARDED_FOR'].split(',')
                self._cached_access_route = [ip.strip() for ip in addresses]
            elif 'HTTP_X_REAL_IP' in self.env:
                self._cached_access_route = [self.env['HTTP_X_REAL_IP']]

            if self._cached_access_route:
                if self._cached_access_route[-1] != self.remote_addr:
                    self._cached_access_route.append(self.remote_addr)
            else:
                self._cached_access_route = [self.remote_addr]

        return self._cached_access_route

    @property
    def remote_addr(self):
        try:
            value = self.env['REMOTE_ADDR']
        except KeyError:
            value = '127.0.0.1'

        return value

    @property
    def port(self):
        try:
            host_header = self.env['HTTP_HOST']

            default_port = 80 if self.env['wsgi.url_scheme'] == 'http' else 443
            host, port = parse_host(host_header, default_port=default_port)
        except KeyError:
            # NOTE(kgriffs): Normalize to an int, since that is the type
            # returned by parse_host().
            #
            # NOTE(kgriffs): In the case that SERVER_PORT was used,
            # PEP-3333 requires that the port never be an empty string.
            port = int(self.env['SERVER_PORT'])

        return port

    @property
    def netloc(self):
        env = self.env
        # NOTE(kgriffs): According to PEP-3333 we should first
        # try to use the Host header if present.
        #
        # PERF(kgriffs): try..except is faster than get() when we
        # expect the key to be present most of the time.
        try:
            netloc_value = env['HTTP_HOST']
        except KeyError:
            netloc_value = env['SERVER_NAME']

            port = env['SERVER_PORT']
            if self.scheme == 'https':
                if port != '443':
                    netloc_value += ':' + port
            else:
                if port != '80':
                    netloc_value += ':' + port

        return netloc_value

    def get_media(self, default_when_empty=_UNSET):
        """Return a deserialized form of the request stream.

        The first time this method is called, the request stream will be
        deserialized using the Content-Type header as well as the media-type
        handlers configured via :class:`falcon.RequestOptions`. The result will
        be cached and returned in subsequent calls::

            deserialized_media = req.get_media()

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

        handler, _, _ = self.options.media_handlers._resolve(
            self.content_type,
            self.options.default_media_type
        )

        try:
            self._media = handler.deserialize(
                self.bounded_stream,
                self.content_type,
                self.content_length
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
                self.bounded_stream.exhaust()

        return self._media

    media = property(get_media)

    # ------------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------------

    def client_accepts(self, media_type):
        """Determine whether or not the client accepts a given media type.

        Args:
            media_type (str): An Internet media type to check.

        Returns:
            bool: ``True`` if the client has indicated in the Accept header
            that it accepts the specified media type. Otherwise, returns
            ``False``.
        """

        accept = self.accept

        # PERF(kgriffs): Usually the following will be true, so
        # try it first.
        if (accept == media_type) or (accept == '*/*'):
            return True

        # Fall back to full-blown parsing
        try:
            return mimeparse.quality(media_type, accept) != 0.0
        except ValueError:
            return False

    def client_prefers(self, media_types):
        """Return the client's preferred media type, given several choices.

        Args:
            media_types (iterable of str): One or more Internet media types
                from which to choose the client's preferred type. This value
                **must** be an iterable collection of strings.

        Returns:
            str: The client's preferred media type, based on the Accept
            header. Returns ``None`` if the client does not accept any
            of the given types.
        """

        try:
            # NOTE(kgriffs): best_match will return '' if no match is found
            preferred_type = mimeparse.best_match(media_types, self.accept)
        except ValueError:
            # Value for the accept header was not formatted correctly
            preferred_type = ''

        return (preferred_type if preferred_type else None)

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

        wsgi_name = name.upper().replace('-', '_')

        # Use try..except to optimize for the header existing in most cases
        try:
            # Don't take the time to cache beforehand, using HTTP naming.
            # This will be faster, assuming that most headers are looked
            # up only once, and not all headers will be requested.
            return self.env['HTTP_' + wsgi_name]

        except KeyError:
            # NOTE(kgriffs): There are a couple headers that do not
            # use the HTTP prefix in the env, so try those. We expect
            # people to usually just use the relevant helper properties
            # to access these instead of .get_header.
            if wsgi_name in WSGI_CONTENT_HEADERS:
                try:
                    return self.env[wsgi_name]
                except KeyError:
                    pass

            if not required:
                return default

            raise errors.HTTPMissingHeader(name)

    def get_header_as_datetime(self, header, required=False, obs_date=False):
        """Return an HTTP header with HTTP-Date values as a datetime.

        Args:
            name (str): Header name, case-insensitive (e.g., 'Date')

        Keyword Args:
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning gracefully when the
                header is not found (default ``False``).
            obs_date (bool): Support obs-date formats according to
                RFC 7231, e.g.: "Sunday, 06-Nov-94 08:49:37 GMT"
                (default ``False``).

        Returns:
            datetime: The value of the specified header if it exists,
            or ``None`` if the header is not found and is not required.

        Raises:
            HTTPBadRequest: The header was not found in the request, but
                it was required.
            HttpInvalidHeader: The header contained a malformed/invalid value.
        """

        try:
            http_date = self.get_header(header, required=required)
            return util.http_date_to_dt(http_date, obs_date=obs_date)
        except TypeError:
            # When the header does not exist and isn't required
            return None
        except ValueError:
            msg = ('It must be formatted according to RFC 7231, '
                   'Section 7.1.1.1')
            raise errors.HTTPInvalidHeader(msg, header)

    def get_cookie_values(self, name):
        """Return all values provided in the Cookie header for the named cookie.

        (See also: :ref:`Getting Cookies <getting-cookies>`)

        Args:
            name (str): Cookie name, case-sensitive.

        Returns:
            list: Ordered list of all values specified in the Cookie header for
            the named cookie, or ``None`` if the cookie was not included in
            the request. If the cookie is specified more than once in the
            header, the returned list of values will preserve the ordering of
            the individual ``cookie-pair``'s in the header.
        """

        if self._cookies is None:
            # PERF(kgriffs): While this code isn't exactly DRY (the same code
            # is duplicated by the cookies property) it does make things a bit
            # more performant by removing the extra function call that would
            # be required to factor this out. If we ever have to do this in a
            # *third* place, we would probably want to factor it out at that
            # point.
            header_value = self.get_header('Cookie')
            if header_value:
                self._cookies = helpers.parse_cookie_header(header_value)
            else:
                self._cookies = {}

        return self._cookies.get(name)

    def get_param(self, name, required=False, store=None, default=None):
        """Return the raw value of a query string parameter as a string.

        Note:
            If an HTML form is POSTed to the API using the
            *application/x-www-form-urlencoded* media type, Falcon can
            automatically parse the parameters from the request body
            and merge them into the query string parameters. To enable
            this functionality, set
            :py:attr:`~.RequestOptions.auto_parse_form_urlencoded` to
            ``True`` via :any:`App.req_options`.

            Note, however, that the
            :attr:`~.RequestOptions.auto_parse_form_urlencoded` option is
            considered deprecated as of Falcon 3.0 in favor of accessing the
            URL-encoded form via :attr:`~Request.media`, and it may be removed
            in a future release.

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

        params = self._params

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            # NOTE(warsaw): If the key appeared multiple times, it will be
            # stored internally as a list.  We do not define which one
            # actually gets returned, but let's pick the last one for grins.
            param = params[name]
            if isinstance(param, list):
                param = param[-1]

            if store is not None:
                store[name] = param

            return param

        if not required:
            return default

        raise errors.HTTPMissingParam(name)

    def get_param_as_int(self, name, required=False, min_value=None,
                         max_value=None, store=None, default=None):
        """Return the value of a query string parameter as an int.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'limit').

        Keyword Args:
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found or is not an integer (default
                ``False``).
            min_value (int): Set to the minimum value allowed for this
                param. If the param is found and it is less than min_value, an
                ``HTTPError`` is raised.
            max_value (int): Set to the maximum value allowed for this
                param. If the param is found and its value is greater than
                max_value, an ``HTTPError`` is raised.
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is found
                (default ``None``).
            default (any): If the param is not found returns the
                given value instead of ``None``

        Returns:
            int: The value of the param if it is found and can be converted to
            an ``int``. If the param is not found, returns ``None``, unless
            `required` is ``True``.

        Raises
            HTTPBadRequest: The param was not found in the request, even though
                it was required to be there, or it was found but could not
                be converted to an ``int``. Also raised if the param's value
                falls outside the given interval, i.e., the value must be in
                the interval: min_value <= value <= max_value to avoid triggering an error.

        """

        params = self._params

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            val = params[name]
            if isinstance(val, list):
                val = val[-1]

            try:
                val = int(val)
            except ValueError:
                msg = 'The value must be an integer.'
                raise errors.HTTPInvalidParam(msg, name)

            if min_value is not None and val < min_value:
                msg = 'The value must be at least ' + str(min_value)
                raise errors.HTTPInvalidParam(msg, name)

            if max_value is not None and max_value < val:
                msg = 'The value may not exceed ' + str(max_value)
                raise errors.HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return default

        raise errors.HTTPMissingParam(name)

    def get_param_as_float(self, name, required=False, min_value=None,
                           max_value=None, store=None, default=None):
        """Return the value of a query string parameter as an float.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'limit').

        Keyword Args:
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found or is not an float (default
                ``False``).
            min_value (float): Set to the minimum value allowed for this
                param. If the param is found and it is less than min_value, an
                ``HTTPError`` is raised.
            max_value (float): Set to the maximum value allowed for this
                param. If the param is found and its value is greater than
                max_value, an ``HTTPError`` is raised.
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is found
                (default ``None``).
            default (any): If the param is not found returns the
                given value instead of ``None``

        Returns:
            float: The value of the param if it is found and can be converted to
            an ``float``. If the param is not found, returns ``None``, unless
            `required` is ``True``.

        Raises
            HTTPBadRequest: The param was not found in the request, even though
                it was required to be there, or it was found but could not
                be converted to an ``float``. Also raised if the param's value
                falls outside the given interval, i.e., the value must be in
                the interval: min_value <= value <= max_value to avoid triggering an error.

        """

        params = self._params

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            val = params[name]
            if isinstance(val, list):
                val = val[-1]

            try:
                val = float(val)
            except ValueError:
                msg = 'The value must be a float.'
                raise errors.HTTPInvalidParam(msg, name)

            if min_value is not None and val < min_value:
                msg = 'The value must be at least ' + str(min_value)
                raise errors.HTTPInvalidParam(msg, name)

            if max_value is not None and max_value < val:
                msg = 'The value may not exceed ' + str(max_value)
                raise errors.HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return default

        raise errors.HTTPMissingParam(name)

    def get_param_as_uuid(self, name, required=False, store=None, default=None):
        """Return the value of a query string parameter as an UUID.

        The value to convert must conform to the standard UUID string
        representation per RFC 4122. For example, the following
        strings are all valid::

            # Lowercase
            '64be949b-3433-4d36-a4a8-9f19d352fee8'

            # Uppercase
            'BE71ECAA-F719-4D42-87FD-32613C2EEB60'

            # Mixed
            '81c8155C-D6de-443B-9495-39Fa8FB239b5'

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'id').

        Keyword Args:
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found or is not a UUID (default
                ``False``).
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is found
                (default ``None``).
            default (any): If the param is not found returns the
                given value instead of ``None``

        Returns:
            UUID: The value of the param if it is found and can be converted to
            a ``UUID``. If the param is not found, returns
            ``default`` (default ``None``), unless `required` is ``True``.

        Raises
            HTTPBadRequest: The param was not found in the request, even though
                it was required to be there, or it was found but could not
                be converted to a ``UUID``.
        """

        params = self._params

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            val = params[name]
            if isinstance(val, list):
                val = val[-1]

            try:
                val = UUID(val)
            except ValueError:
                msg = 'The value must be a UUID string.'
                raise errors.HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return default

        raise errors.HTTPMissingParam(name)

    def get_param_as_bool(self, name, required=False, store=None,
                          blank_as_true=True, default=None):
        """Return the value of a query string parameter as a boolean.

        This method treats valueless parameters as flags. By default, if no
        value is provided for the parameter in the query string, ``True`` is
        assumed and returned. If the parameter is missing altogether, ``None``
        is returned as with other ``get_param_*()`` methods, which can be
        easily treated as falsy by the caller as needed.

        The following boolean strings are supported::

            TRUE_STRINGS = ('true', 'True', 't', 'yes', 'y', '1', 'on')
            FALSE_STRINGS = ('false', 'False', 'f', 'no', 'n', '0', 'off')

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'detailed').

        Keyword Args:
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found or is not a recognized boolean
                string (default ``False``).
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is found (default
                ``None``).
            blank_as_true (bool): Valueless query string parameters
                are treated as flags, resulting in ``True`` being
                returned when such a parameter is present, and ``False``
                otherwise. To require the client to explicitly opt-in to a
                truthy value, pass ``blank_as_true=False`` to return ``False``
                when a value is not specified in the query string.
            default (any): If the param is not found, return this
                value instead of ``None``.

        Returns:
            bool: The value of the param if it is found and can be converted
            to a ``bool``. If the param is not found, returns ``None``
            unless `required` is ``True``.

        Raises:
            HTTPBadRequest: A required param is missing from the request, or
                can not be converted to a ``bool``.

        """

        params = self._params

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            val = params[name]
            if isinstance(val, list):
                val = val[-1]

            if val in TRUE_STRINGS:
                val = True
            elif val in FALSE_STRINGS:
                val = False
            elif not val:
                val = blank_as_true
            else:
                msg = 'The value of the parameter must be "true" or "false".'
                raise errors.HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return default

        raise errors.HTTPMissingParam(name)

    def get_param_as_list(self, name, transform=None,
                          required=False, store=None, default=None):
        """Return the value of a query string parameter as a list.

        List items must be comma-separated or must be provided
        as multiple instances of the same param in the query string
        ala *application/x-www-form-urlencoded*.

        Note:
            To enable the interpretation of comma-separated parameter values,
            the :attr:`~falcon.RequestOptions.auto_parse_qs_csv` option must
            be set to ``True`` (default ``False``).

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'ids').

        Keyword Args:
            transform (callable): An optional transform function
                that takes as input each element in the list as a ``str`` and
                outputs a transformed element for inclusion in the list that
                will be returned. For example, passing ``int`` will
                transform list items into numbers.
            required (bool): Set to ``True`` to raise ``HTTPBadRequest``
                instead of returning ``None`` when the parameter is not
                found (default ``False``).
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is found (default
                ``None``).
            default (any): If the param is not found returns the
                given value instead of ``None``

        Returns:
            list: The value of the param if it is found. Otherwise, returns
            ``None`` unless *required* is ``True``.

            Empty list elements will be included by default, but this behavior
            can be configured by setting the
            :attr:`~falcon.RequestOptions.keep_blank_qs_values` option. For
            example, by default the following query strings would both result in
            ``['1', '', '3']``::

                things=1&things=&things=3
                things=1,,3

            Note, however, that for the second example string above to be
            interpreted as a list, the
            :attr:`~falcon.RequestOptions.auto_parse_qs_csv` option must be
            set to ``True``.

        Raises:
            HTTPBadRequest: A required param is missing from the request, or
                a transform function raised an instance of ``ValueError``.

        """

        params = self._params

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            items = params[name]

            # NOTE(warsaw): When a key appears multiple times in the request
            # query, it will already be represented internally as a list.
            # NOTE(kgriffs): Likewise for comma-delimited values.
            if not isinstance(items, list):
                items = [items]

            # PERF(kgriffs): Use if-else rather than a DRY approach
            # that sets transform to a passthrough function; avoids
            # function calling overhead.
            if transform is not None:
                try:
                    items = [transform(i) for i in items]

                except ValueError:
                    msg = 'The value is not formatted correctly.'
                    raise errors.HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = items

            return items

        if not required:
            return default

        raise errors.HTTPMissingParam(name)

    def get_param_as_datetime(self, name, format_string='%Y-%m-%dT%H:%M:%SZ',
                              required=False, store=None, default=None):
        """Return the value of a query string parameter as a datetime.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'ids').

        Keyword Args:
            format_string (str): String used to parse the param value
                into a ``datetime``. Any format recognized by strptime() is
                supported (default ``'%Y-%m-%dT%H:%M:%SZ'``).
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found (default ``False``).
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is found (default
                ``None``).
            default (any): If the param is not found returns the
                given value instead of ``None``
        Returns:
            datetime.datetime: The value of the param if it is found and can be
            converted to a ``datetime`` according to the supplied format
            string. If the param is not found, returns ``None`` unless
            required is ``True``.

        Raises:
            HTTPBadRequest: A required param is missing from the request, or
                the value could not be converted to a ``datetime``.
        """

        param_value = self.get_param(name, required=required)

        if param_value is None:
            return default

        try:
            date_time = strptime(param_value, format_string)
        except ValueError:
            msg = 'The date value does not match the required format.'
            raise errors.HTTPInvalidParam(msg, name)

        if store is not None:
            store[name] = date_time

        return date_time

    def get_param_as_date(self, name, format_string='%Y-%m-%d',
                          required=False, store=None, default=None):
        """Return the value of a query string parameter as a date.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'ids').

        Keyword Args:
            format_string (str): String used to parse the param value
                into a date. Any format recognized by strptime() is
                supported (default ``"%Y-%m-%d"``).
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found (default ``False``).
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is found (default
                ``None``).
            default (any): If the param is not found returns the
                given value instead of ``None``
        Returns:
            datetime.date: The value of the param if it is found and can be
            converted to a ``date`` according to the supplied format
            string. If the param is not found, returns ``None`` unless
            required is ``True``.

        Raises:
            HTTPBadRequest: A required param is missing from the request, or
                the value could not be converted to a ``date``.
        """

        date_time = self.get_param_as_datetime(name, format_string, required)
        if date_time:
            date = date_time.date()
        else:
            return default

        if store is not None:
            store[name] = date

        return date

    def get_param_as_json(self, name, required=False, store=None, default=None):
        """Return the decoded JSON value of a query string parameter.

        Given a JSON value, decode it to an appropriate Python type,
        (e.g., ``dict``, ``list``, ``str``, ``int``, ``bool``, etc.)

        Warning:
            If the :attr:`~falcon.RequestOptions.auto_parse_qs_csv` option is
            set to ``True`` (default ``False``), the framework will
            misinterpret any JSON values that include literal
            (non-percent-encoded) commas. If the query string may include
            JSON, you can use JSON array syntax in lieu of CSV as a workaround.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'payload').

        Keyword Args:
            required (bool): Set to ``True`` to raise ``HTTPBadRequest``
                instead of returning ``None`` when the parameter is not
                found (default ``False``).
            store (dict): A ``dict``-like object in which to place the
                value of the param, but only if the param is found
                (default ``None``).
            default (any): If the param is not found returns the
                given value instead of ``None``

        Returns:
            dict: The value of the param if it is found. Otherwise, returns
            ``None`` unless required is ``True``.

        Raises:
            HTTPBadRequest: A required param is missing from the request, or
                the value could not be parsed as JSON.
        """

        param_value = self.get_param(name, required=required)

        if param_value is None:
            return default

        handler, _, _ = self.options.media_handlers._resolve(
            MEDIA_JSON, MEDIA_JSON, raise_not_found=False
        )
        if handler is None:
            handler = _DEFAULT_JSON_HANDLER

        try:
            # TODO(CaselIT): find a way to avoid encode + BytesIO if handlers
            # interface is refactored. Possibly using the WS interface?
            val = handler.deserialize(
                BytesIO(param_value.encode()), MEDIA_JSON, len(param_value)
            )
        except errors.HTTPBadRequest:
            msg = 'It could not be parsed as JSON.'
            raise errors.HTTPInvalidParam(msg, name)

        if store is not None:
            store[name] = val

        return val

    def has_param(self, name):
        """Determine whether or not the query string parameter already exists.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'sort').

        Returns:
            bool: ``True`` if param is found, or ``False`` if param is
            not found.

        """

        if name in self._params:
            return True
        else:
            return False

    def log_error(self, message):
        """Write an error message to the server's log.

        Prepends timestamp and request info to message, and writes the
        result out to the WSGI server's error stream (`wsgi.error`).

        Args:
            message (str): Description of the problem.

        """

        if self.query_string:
            query_string_formatted = '?' + self.query_string
        else:
            query_string_formatted = ''

        log_line = (
            DEFAULT_ERROR_LOG_FORMAT.
            format(now(), self.method, self.path, query_string_formatted)
        )

        self._wsgierrors.write(log_line + message + '\n')

    # ------------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------------

    def _get_wrapped_wsgi_input(self):
        try:
            content_length = self.content_length or 0

        # NOTE(kgriffs): This branch is indeed covered in test_wsgi.py
        # even though coverage isn't able to detect it.
        except errors.HTTPInvalidHeader:  # pragma: no cover
            # NOTE(kgriffs): The content-length header was specified,
            # but it had an invalid value. Assume no content.
            content_length = 0

        return BoundedStream(self.env['wsgi.input'], content_length)

    def _parse_form_urlencoded(self):
        content_length = self.content_length
        if not content_length:
            return

        body = self.stream.read(content_length)

        # NOTE(kgriffs): According to http://goo.gl/6rlcux the
        # body should be US-ASCII. Enforcing this also helps
        # catch malicious input.
        try:
            body = body.decode('ascii')
        except UnicodeDecodeError:
            body = None
            self.log_error('Non-ASCII characters found in form body '
                           'with Content-Type of '
                           'application/x-www-form-urlencoded. Body '
                           'will be ignored.')

        if body:
            extra_params = parse_query_string(
                body,
                keep_blank=self.options.keep_blank_qs_values,
                csv=self.options.auto_parse_qs_csv,
            )

            self._params.update(extra_params)


# PERF: To avoid typos and improve storage space and speed over a dict.
class RequestOptions:
    """Defines a set of configurable request options.

    An instance of this class is exposed via :attr:`falcon.App.req_options` and
    :attr:`falcon.asgi.App.req_options` for configuring certain
    :class:`~.Request` and :class:`falcon.asgi.Request` behaviors,
    respectively.

    Attributes:
        keep_blank_qs_values (bool): Set to ``False`` to ignore query string
            params that have missing or blank values (default ``True``).
            For comma-separated values, this option also determines
            whether or not empty elements in the parsed list are
            retained.

        auto_parse_form_urlencoded: Set to ``True`` in order to
            automatically consume the request stream and merge the
            results into the request's query string params when the
            request's content type is
            *application/x-www-form-urlencoded* (default ``False``).

            Enabling this option for WSGI apps makes the form parameters
            accessible via :attr:`~falcon.Request.params`,
            :meth:`~falcon.Request.get_param`, etc.

            Warning:
                The `auto_parse_form_urlencoded` option is not supported for
                ASGI apps, and is considered deprecated for WSGI apps as of
                Falcon 3.0, in favor of accessing URL-encoded forms
                through :attr:`~Request.media`.

                See also: :ref:`access_urlencoded_form`

            Warning:
                When this option is enabled, the request's body
                stream will be left at EOF. The original data is
                not retained by the framework.

            Note:
                The character encoding for fields, before
                percent-encoding non-ASCII bytes, is assumed to be
                UTF-8. The special `_charset_` field is ignored if
                present.

                Falcon expects form-encoded request bodies to be
                encoded according to the standard W3C algorithm (see
                also http://goo.gl/6rlcux).

        auto_parse_qs_csv: Set to ``True`` to split query string values on
            any non-percent-encoded commas (default ``False``).

            When ``False``,
            values containing commas are left as-is. In this mode, list items
            are taken only from multiples of the same parameter name within the
            query string (i.e. ``t=1,2,3&t=4`` becomes ``['1,2,3', '4']``).

            When `auto_parse_qs_csv` is set to ``True``, the query string value
            is also split on non-percent-encoded commas and these items
            are added to the final list (i.e. ``t=1,2,3&t=4,5``
            becomes ``['1', '2', '3', '4', '5']``).

            Warning:
                Enabling this option will cause the framework to misinterpret
                any JSON values that include literal (non-percent-encoded)
                commas. If the query string may include JSON, you can
                use JSON array syntax in lieu of CSV as a workaround.

        strip_url_path_trailing_slash: Set to ``True`` in order to
            strip the trailing slash, if present, at the end of the URL
            path (default ``False``). When this option is enabled,
            the URL path is normalized by stripping the trailing slash
            character. This lets the application define a single route
            to a resource for a path that may or may not end in a
            forward slash. However, this behavior can be problematic in
            certain cases, such as when working with authentication
            schemes that employ URL-based signatures.

        default_media_type (str): The default media-type used to
            deserialize a request body, when the Content-Type header is
            missing or ambiguous. This value is normally
            set to the media type provided to the :class:`falcon.App` or
            :class:`falcon.asgi.App` initializer; however, if created
            independently, this will default to
            :attr:`falcon.DEFAULT_MEDIA_TYPE`.

        media_handlers (Handlers): A dict-like object for configuring the
            media-types to handle. By default, handlers are provided for the
            ``application/json``, ``application/x-www-form-urlencoded`` and
            ``multipart/form-data`` media types.
    """
    __slots__ = (
        'keep_blank_qs_values',
        'auto_parse_form_urlencoded',
        'auto_parse_qs_csv',
        'strip_url_path_trailing_slash',
        'default_media_type',
        'media_handlers',
    )

    def __init__(self):
        self.keep_blank_qs_values = True
        self.auto_parse_form_urlencoded = False
        self.auto_parse_qs_csv = False
        self.strip_url_path_trailing_slash = False
        self.default_media_type = DEFAULT_MEDIA_TYPE
        self.media_handlers = Handlers()
