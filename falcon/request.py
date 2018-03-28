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

import cgi
from datetime import datetime
import os
from sys import exc_info
import tempfile

try:
    # NOTE(kgrifs): In Python 2.6 and 2.7, socket._fileobject is a
    # standard way of exposing a socket as a file-like object, and
    # is used by wsgiref for wsgi.input.
    import socket
    NativeStream = socket._fileobject
except AttributeError:
    # NOTE(kgriffs): In Python 3.3, wsgiref implements wsgi.input
    # using _io.BufferedReader which is an alias of io.BufferedReader
    import io
    NativeStream = io.BufferedReader

from uuid import UUID  # NOQA: I202
from wsgiref.validate import InputWrapper

try:
    # NOTE(kgriffs): In Python 3+, we need html.unescape to decode html encoded characters
    import html.parser
    DECODE_HTML_CHARS = html.parser.HTMLParser().unescape
except ImportError:
    # NOTE(kgriffs): In Python 2+, we need HTMLParser to decode html encoded characters
    from HTMLParser import HTMLParser
    HP = HTMLParser()

    def DECODE_HTML_CHARS(raw_str):
        return HP.unescape(raw_str).encode('utf-8')


import mimeparse
import six
from six.moves import http_cookies

from falcon import DEFAULT_MEDIA_TYPE
from falcon import errors
from falcon import request_helpers as helpers
from falcon import util
from falcon.forwarded import _parse_forwarded_header
from falcon.forwarded import Forwarded  # NOQA
from falcon.media import Handlers
from falcon.util import json
from falcon.util.uri import parse_host, parse_query_string

# NOTE(tbug): In some cases, http_cookies is not a module
# but a dict-like structure. This fixes that issue.
# See issue https://github.com/falconry/falcon/issues/556
SimpleCookie = http_cookies.SimpleCookie

DEFAULT_ERROR_LOG_FORMAT = (u'{0:%Y-%m-%d %H:%M:%S} [FALCON] [ERROR]'
                            u' {1} {2}{3} => ')

TRUE_STRINGS = ('true', 'True', 'yes', '1', 'on')
FALSE_STRINGS = ('false', 'False', 'no', '0', 'off')
WSGI_CONTENT_HEADERS = ('CONTENT_TYPE', 'CONTENT_LENGTH')

# PERF(kgriffs): Avoid an extra namespace lookup when using these functions
strptime = datetime.strptime
now = datetime.now


class Request(object):
    """Represents a client's HTTP request.

    Note:
        `Request` is not meant to be instantiated directly by responders.

    Args:
        env (dict): A WSGI environment dict passed in from the server. See
            also PEP-3333.

    Keyword Arguments:
        options (dict): Set of global options passed from the API handler.

    Attributes:
        env (dict): Reference to the WSGI environ ``dict`` passed in from the
            server. (See also PEP-3333.)
        context (dict): Dictionary to hold any data about the request which is
            specific to your app (e.g. session object). Falcon itself will
            not interact with this attribute after it has been initialized.
        context_type (class): Class variable that determines the factory or
            type to use for initializing the `context` attribute. By default,
            the framework will instantiate standard ``dict`` objects. However,
            you may override this behavior by creating a custom child class of
            ``falcon.Request``, and then passing that new class to
            `falcon.API()` by way of the latter's `request_type` parameter.

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

        protocol (str): Deprecated alias for `scheme`. Will be removed
            in a future release.
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

        port (int): Port used for the request. If the request URI does
            not specify a port, the default one for the given schema is
            returned (80 for HTTP and 443 for HTTPS).
        netloc (str): Returns the 'host:port' portion of the request
            URL. The port may be ommitted if it is the default one for
            the URL's schema (80 for HTTP and 443 for HTTPS).
        subdomain (str): Leftmost (i.e., most specific) subdomain from the
            hostname. If only a single domain name is given, `subdomain`
            will be ``None``.

            Note:
                If the hostname in the request is an IP address, the value
                for `subdomain` is undefined.

        app (str): The initial portion of the request URI's path that
            corresponds to the application object, so that the
            application knows its virtual "location". This may be an
            empty string, if the application corresponds to the "root"
            of the server.

            (Corresponds to the "SCRIPT_NAME" environ variable defined
            by PEP-3333.)
        uri (str): The fully-qualified URI for the request.
        url (str): Alias for `uri`.
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

            Note:
                `req.path` may be set to a new value by a `process_request()`
                middleware method in order to influence routing.
        query_string (str): Query string portion of the request URI, without
            the preceding '?' character.
        uri_template (str): The template for the route that was matched for
            this request. May be ``None`` if the request has not yet been
            routed, as would be the case for `process_request()` middleware
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
        accept (str): Value of the Accept header, or '*/*' if the header is
            missing.
        client_accepts_json (bool): ``True`` if the Accept header indicates
            that the client is willing to receive JSON, otherwise ``False``.
        client_accepts_msgpack (bool): ``True`` if the Accept header indicates
            that the client is willing to receive MessagePack, otherwise
            ``False``.
        client_accepts_xml (bool): ``True`` if the Accept header indicates that
            the client is willing to receive XML, otherwise ``False``.
        cookies (dict):
            A dict of name/value cookie pairs. (See also:
            :ref:`Getting Cookies <getting-cookies>`)
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

        expect (str): Value of the Expect header, or ``None`` if the
            header is missing.
        media (object): Returns a deserialized form of the request stream.
            When called, it will attempt to deserialize the request stream
            using the Content-Type header as well as the media-type handlers
            configured via :class:`falcon.RequestOptions`.

            See :ref:`media` for more information regarding media handling.

            Warning:
                This operation will consume the request stream the first time
                it's called and cache the results. Follow-up calls will just
                retrieve a cached version of the object.

        range (tuple of int): A 2-member ``tuple`` parsed from the value of the
            Range header.

            The two members correspond to the first and last byte
            positions of the requested resource, inclusive. Negative
            indices indicate offset from the end of the resource,
            where -1 is the last byte, -2 is the second-to-last byte,
            and so forth.

            Only continous ranges are supported (e.g., "bytes=0-0,-1" would
            result in an HTTPBadRequest exception when the attribute is
            accessed.)
        range_unit (str): Unit of the range parsed from the value of the
            Range header, or ``None`` if the header is missing
        if_match (str): Value of the If-Match header, or ``None`` if the
            header is missing.
        if_none_match (str): Value of the If-None-Match header, or ``None``
            if the header is missing.
        if_modified_since (datetime): Value of the If-Modified-Since header,
            or ``None`` if the header is missing.
        if_unmodified_since (datetime): Value of the If-Unmodified-Since
            header, or ``None`` if the header is missing.
        if_range (str): Value of the If-Range header, or ``None`` if the
            header is missing.

        headers (dict): Raw HTTP headers from the request with
            canonical dash-separated names. Parsing all the headers
            to create this dict is done the first time this attribute
            is accessed. This parsing can be costly, so unless you
            need all the headers in this format, you should use the
            `get_header` method or one of the convenience attributes
            instead, to get a value for a specific header.

        params (dict): The mapping of request query parameter names to their
            values.  Where the parameter appears multiple times in the query
            string, the value mapped to that parameter key will be a list of
            all the values in the order seen.

        form_data (dict): The mapping of application/x-www-form-urlencoded
            or multipart/data request parameter names to their values.
            When the parameter appears multiple times in the request payload body,
            the value mapped to that parameter key will be a list of all
            the values in the order seen.

        files (dict): The mapping of multipart/data request filename
            to their FileStream object. When the filename appears
            multiple times in the request payload body, the value mapped
            to that filename key will be a list of all the FileStream
            objects in the order seen.

        options (dict): Set of global options passed from the API handler.
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
        '_cookies',
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
        '_form_data',
        '_files'
    )

    # Child classes may override this
    context_type = dict

    _wsgi_input_type_known = False
    _always_wrap_wsgi_input = False

    def __init__(self, env, options=None):
        self.env = env
        self.options = options if options else RequestOptions()

        self._wsgierrors = env['wsgi.errors']
        self.method = env['REQUEST_METHOD']

        self.uri_template = None
        self._media = None

        # NOTE(kgriffs): PEP 3333 specifies that PATH_INFO may be the
        # empty string, so normalize it in that case.
        path = env['PATH_INFO'] or '/'

        if six.PY3:
            # PEP 3333 specifies that PATH_INFO variable are always
            # "bytes tunneled as latin-1" and must be encoded back
            path = path.encode('latin1').decode('utf-8', 'replace')

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
                    keep_blank_qs_values=self.options.keep_blank_qs_values,
                    parse_qs_csv=self.options.auto_parse_qs_csv,
                )

            else:
                self._params = {}

        self._cookies = None

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

        # NOTE(kgriffs): Wrap wsgi.input if needed to make read() more robust,
        # normalizing semantics between, e.g., gunicorn and wsgiref.
        #
        # PERF(kgriffs): Accessing via self when reading is faster than
        # via the class name. But we must set the variables using the
        # class name so they are picked up by all future instantiations
        # of the class.
        if not self._wsgi_input_type_known:
            Request._always_wrap_wsgi_input = isinstance(
                env['wsgi.input'],
                (NativeStream, InputWrapper)
            )

            Request._wsgi_input_type_known = True

        if self._always_wrap_wsgi_input:
            # TODO(kgriffs): In Falcon 2.0, stop wrapping stream since it is
            # less useful now that we have bounded_stream.
            self.stream = self._get_wrapped_wsgi_input()
            self._bounded_stream = self.stream
        else:
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

        # NOTE(kgriffs): Store input params in _form_data and files in _files
        self._files = None
        self._form_data = None

    def __repr__(self):
        return '<%s: %s %r>' % (self.__class__.__name__, self.method, self.url)

    # ------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------

    user_agent = helpers.header_property('HTTP_USER_AGENT')
    auth = helpers.header_property('HTTP_AUTHORIZATION')

    expect = helpers.header_property('HTTP_EXPECT')

    if_match = helpers.header_property('HTTP_IF_MATCH')
    if_none_match = helpers.header_property('HTTP_IF_NONE_MATCH')
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
            # PERF(kgriffs): If someone is calling this, they are probably
            # confident that the header exists, so most of the time we
            # expect this call to succeed. Therefore, we won't need to
            # pay the penalty of a raised exception in most cases, and
            # there is no need to spend extra cycles calling get() or
            # checking beforehand whether the key is in the dict.
            try:
                forwarded = self.env['HTTP_FORWARDED']
            except KeyError:
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
    def if_modified_since(self):
        return self.get_header_as_datetime('If-Modified-Since')

    @property
    def if_unmodified_since(self):
        return self.get_header_as_datetime('If-Unmodified-Since')

    @property
    def range(self):
        try:
            value = self.env['HTTP_RANGE']
            if '=' in value:
                unit, sep, req_range = value.partition('=')
            else:
                msg = "The value must be prefixed with a range unit, e.g. 'bytes='"
                raise errors.HTTPInvalidHeader(msg, 'Range')
        except KeyError:
            return None

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
            msg = ('It must be a range formatted according to RFC 7233.')
            raise errors.HTTPInvalidHeader(msg, 'Range', href=href,
                                           href_text=href_text)

    @property
    def range_unit(self):
        try:
            value = self.env['HTTP_RANGE']

            if '=' in value:
                unit, sep, req_range = value.partition('=')
                return unit
            else:
                msg = "The value must be prefixed with a range unit, e.g. 'bytes='"
                raise errors.HTTPInvalidHeader(msg, 'Range')
        except KeyError:
            return None

    @property
    def app(self):
        # PERF(kgriffs): try..except is faster than get() assuming that
        # we normally expect the key to exist. Even though PEP-3333
        # allows WSGI servers to omit the key when the value is an
        # empty string, uwsgi, gunicorn, waitress, and wsgiref all
        # include it even in that case.
        try:
            return self.env['SCRIPT_NAME']
        except KeyError:
            return ''

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

    # TODO(kgriffs): Remove this deprecated alias in Falcon 2.0
    protocol = scheme

    @property
    def uri(self):
        if self._cached_uri is None:
            scheme = self.env['wsgi.url_scheme']

            # PERF: For small numbers of items, '+' is faster
            # than ''.join(...). Concatenation is also generally
            # faster than formatting.
            value = (scheme + '://' +
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
                self.env['wsgi.url_scheme'] + '://' +
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
            host = first_hop.host or self.host
        else:
            # PERF(kgriffs): This call should normally succeed, assuming
            # that the caller is expecting a forwarded header, so
            # just go for it without wasting time checking it
            # first.
            try:
                host = self.env['HTTP_X_FORWARDED_HOST']
            except KeyError:
                host = self.host

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

        return self._cached_headers.copy()

    @property
    def params(self):
        return self._params

    @property
    def form_data(self):
        if self._form_data is None:
            self._parse_form_urlencoded_or_multipart_form()
        return self._form_data

    @property
    def files(self):
        if self._files is None:
            self._parse_form_urlencoded_or_multipart_form()
        return self._files

    @property
    def cookies(self):
        if self._cookies is None:
            # NOTE(tbug): We might want to look into parsing
            # cookies ourselves. The SimpleCookie is doing a
            # lot if stuff only required to SEND cookies.
            cookie_header = self.get_header('Cookie', default='')
            parser = SimpleCookie()
            for cookie_part in cookie_header.split('; '):
                try:
                    parser.load(cookie_part)
                except http_cookies.CookieError:
                    pass
            cookies = {}
            for morsel in parser.values():
                cookies[morsel.key] = morsel.value

            self._cookies = cookies

        return self._cookies.copy()

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
            elif 'REMOTE_ADDR' in self.env:
                self._cached_access_route = [self.env['REMOTE_ADDR']]
            else:
                self._cached_access_route = []

        return self._cached_access_route

    @property
    def remote_addr(self):
        return self.env.get('REMOTE_ADDR')

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
        protocol = env['wsgi.url_scheme']

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
            if protocol == 'https':
                if port != '443':
                    netloc_value += ':' + port
            else:
                if port != '80':
                    netloc_value += ':' + port

        return netloc_value

    @property
    def media(self):
        if self._media:
            return self._media

        handler = self.options.media_handlers.find_by_media_type(
            self.content_type,
            self.options.default_media_type
        )

        # Consume the stream
        raw = self.bounded_stream.read()

        # Deserialize and Return
        self._media = handler.deserialize(raw)
        return self._media

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

    def get_param(self, name, required=False, store=None, default=None):
        """Return the raw value of a query string parameter as a string.

        Note:
            If an HTML form is POSTed to the API using the
            *application/x-www-form-urlencoded* media type, Falcon can
            automatically parse the parameters from the request body
            and merge them into the query string parameters. To enable
            this functionality, set
            :py:attr:`~.RequestOptions.auto_parse_form_urlencoded` to
            ``True`` via :any:`API.req_options`.

        Note:
            Similar to the way multiple keys in form data is handled,
            if a query parameter is assigned a comma-separated list of
            values (e.g., ``foo=a,b,c``), only one of those values will be
            returned, and it is undefined which one. Use
            :meth:`~.get_param_as_list` to retrieve all the values.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'sort').

        Keyword Args:
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found (default ``False``).
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is present.
            default (any): If the param is not found returns the
                given value instead of None

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

    def get_param_as_int(self, name,
                         required=False, min=None, max=None, store=None):
        """Return the value of a query string parameter as an int.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'limit').

        Keyword Args:
            required (bool): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found or is not an integer (default
                ``False``).
            min (int): Set to the minimum value allowed for this
                param. If the param is found and it is less than min, an
                ``HTTPError`` is raised.
            max (int): Set to the maximum value allowed for this
                param. If the param is found and its value is greater than
                max, an ``HTTPError`` is raised.
            store (dict): A ``dict``-like object in which to place
                the value of the param, but only if the param is found
                (default ``None``).

        Returns:
            int: The value of the param if it is found and can be converted to
            an ``int``. If the param is not found, returns ``None``, unless
            `required` is ``True``.

        Raises
            HTTPBadRequest: The param was not found in the request, even though
                it was required to be there, or it was found but could not
                be converted to an ``int``. Also raised if the param's value
                falls outside the given interval, i.e., the value must be in
                the interval: min <= value <= max to avoid triggering an error.

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

            if min is not None and val < min:
                msg = 'The value must be at least ' + str(min)
                raise errors.HTTPInvalidParam(msg, name)

            if max is not None and max < val:
                msg = 'The value may not exceed ' + str(max)
                raise errors.HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return None

        raise errors.HTTPMissingParam(name)

    def get_param_as_uuid(self, name, required=False, store=None):
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

        Returns:
            UUID: The value of the param if it is found and can be converted to
            a ``UUID``. If the param is not found, returns ``None``, unless
            `required` is ``True``.

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
            return None

        raise errors.HTTPMissingParam(name)

    def get_param_as_bool(self, name, required=False, store=None,
                          blank_as_true=False):
        """Return the value of a query string parameter as a boolean

        The following boolean strings are supported::

            TRUE_STRINGS = ('true', 'True', 'yes', '1', 'on')
            FALSE_STRINGS = ('false', 'False', 'no', '0', 'off')

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
            blank_as_true (bool): If ``True``, an empty string value will be
                treated as ``True`` (default ``False``). Normally empty strings
                are ignored; if you would like to recognize such parameters, you
                must set the `keep_blank_qs_values` request option to ``True``.
                Request options are set globally for each instance of
                ``falcon.API`` through the `req_options` attribute.

        Returns:
            bool: The value of the param if it is found and can be converted
            to a ``bool``. If the param is not found, returns ``None``
            unless required is ``True``.

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
            elif blank_as_true and not val:
                val = True
            else:
                msg = 'The value of the parameter must be "true" or "false".'
                raise errors.HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return None

        raise errors.HTTPMissingParam(name)

    def get_param_as_list(self, name,
                          transform=None, required=False, store=None):
        """Return the value of a query string parameter as a list.

        List items must be comma-separated or must be provided
        as multiple instances of the same param in the query string
        ala *application/x-www-form-urlencoded*.

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

        Returns:
            list: The value of the param if it is found. Otherwise, returns
            ``None`` unless required is True. Empty list elements will be
            discarded. For example, the following query strings would
            both result in `['1', '3']`::

                things=1,,3
                things=1&things=&things=3

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
            return None

        raise errors.HTTPMissingParam(name)

    def get_param_as_datetime(self, name, format_string='%Y-%m-%dT%H:%M:%SZ',
                              required=False, store=None):
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
            return None

        try:
            date_time = strptime(param_value, format_string)
        except ValueError:
            msg = 'The date value does not match the required format.'
            raise errors.HTTPInvalidParam(msg, name)

        if store is not None:
            store[name] = date_time

        return date_time

    def get_param_as_date(self, name, format_string='%Y-%m-%d',
                          required=False, store=None):
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
            return None

        if store is not None:
            store[name] = date

        return date

    def get_param_as_json(self, name, required=False, store=None):
        """Return the decoded JSON value of a query string parameter.

        Given a JSON value, decode it to an appropriate Python type,
        (e.g., ``dict``, ``list``, ``str``, ``int``, ``bool``, etc.)

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'payload').

        Keyword Args:
            required (bool): Set to ``True`` to raise ``HTTPBadRequest``
                instead of returning ``None`` when the parameter is not
                found (default ``False``).
            store (dict): A ``dict``-like object in which to place the
                value of the param, but only if the param is found
                (default ``None``).

        Returns:
            dict: The value of the param if it is found. Otherwise, returns
            ``None`` unless required is ``True``.

        Raises:
            HTTPBadRequest: A required param is missing from the request, or
                the value could not be parsed as JSON.
        """

        param_value = self.get_param(name, required=required)

        if param_value is None:
            return None

        try:
            val = json.loads(param_value)
        except ValueError:
            msg = 'It could not be parsed as JSON.'
            raise errors.HTTPInvalidParam(msg, name)

        if store is not None:
            store[name] = val

        return val

    get_param_as_dict = get_param_as_json
    """Deprecated alias of :meth:`~get_param_as_json`.

    Warning:

        This method has been deprecated and will be removed in a future release.
    """

    def log_error(self, message):
        """Write an error message to the server's log.

        Prepends timestamp and request info to message, and writes the
        result out to the WSGI server's error stream (`wsgi.error`).

        Args:
            message (str or unicode): Description of the problem. On Python 2,
                instances of ``unicode`` will be converted to UTF-8.

        """

        if self.query_string:
            query_string_formatted = '?' + self.query_string
        else:
            query_string_formatted = ''

        log_line = (
            DEFAULT_ERROR_LOG_FORMAT.
            format(now(), self.method, self.path, query_string_formatted)
        )

        if six.PY3:
            self._wsgierrors.write(log_line + message + '\n')
        else:
            if isinstance(message, unicode):
                message = message.encode('utf-8')

            self._wsgierrors.write(log_line.encode('utf-8'))
            self._wsgierrors.write(message + '\n')

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

        return helpers.BoundedStream(self.env['wsgi.input'], content_length)

    def _getFieldValue(self, field):
        """Returns input value for imput text fields and FileStream object
        for input file and None if no file is selected for upload

        Args:
            field (cgi.FieldStorage or cgi.MiniFieldStorage).
        """
        if field.file and 'filename' in field.disposition_options:

            # read first byte of file buffer to make sure if file content exists
            first_byte = field.file.read(1)

            if first_byte:
                # NOTE(kgriffs): This is an uploaded file.
                return FileStream(
                    file_buffer=field,
                    max_size=self.options.file_max_upload_size,
                    first_byte=first_byte
                )
            else:
                # NOTE(kgriffs): No contents found which means no file uploaded.
                return None
        else:
            # NOTE(kgriffs): This is an text field.
            # DECODE_HTML_CHARS is used to convert html code to utf-8 charcters
            return DECODE_HTML_CHARS(field.value)

    def _parse_form_urlencoded_or_multipart_form(self):
        """Parses urlencoded or multipart form data.
        It sets text fileds in _form_data dict and file buffers in _files dict.
        """

        if (
            self.method not in ('GET', 'HEAD') and
            self.content_type is not None and
            (
                'multipart/form-data' in self.content_type or
                'application/x-www-form-urlencoded' in self.content_type
            )
        ):
            # NOTE(kgriffs): Store input params in _form_data and files in _files
            self._files = {}
            self._form_data = {}
        else:
            return

        field_storage = cgi.FieldStorage(fp=self.stream, environ=self.env)
        for fieldname in field_storage.keys():
            filedata = field_storage[fieldname]
            if isinstance(filedata, list):
                # NOTE(kgriffs): fieldname has multiple values
                list_data = []
                list_files = []
                for item in filedata:
                    value = self._getFieldValue(item)
                    if isinstance(value, str):
                        list_data.append(value)
                    elif value:
                        list_files.append(value)
                if list_data:
                    self._form_data[fieldname] = list_data
                if list_files:
                    self._files[fieldname] = list_files
            else:
                # NOTE(kgriffs): fieldname has single values
                value = self._getFieldValue(filedata)
                if isinstance(value, str):
                    self._form_data[fieldname] = value
                elif value:
                    self._files[fieldname] = value

        for i in list(self._form_data):
            if isinstance(self._form_data[i], list) and len(self._form_data[i]) == 1:
                self._form_data[i] = self._form_data[i][0]

        for i in list(self._files):
            if isinstance(self._files[i], list) and len(self._files[i]) == 1:
                self._files[i] = self._files[i][0]

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
                keep_blank_qs_values=self.options.keep_blank_qs_values,
                parse_qs_csv=self.options.auto_parse_qs_csv,
            )

            self._params.update(extra_params)


class FileStream(object):
    """
    Defines a set of configurable options to handle file upload and file buffering
    Note:
        `FileStream` is not meant to be instantiated directly by responders.

    Args:
        fbuffer : io Buffer of file being uploaded.
        max_size : Maximum allowed number of bytes of file being uploaded.
        first_byte: First byte of file buffer

    Attributes:
        name : Name of file being uploaded.
        type : Content type of file being uploaded.
        _buffer : io Buffer of file being uploaded.
        _max_size : io Buffer of file being uploaded.
        _temp_file : Temporary location of file being uploaded.
        error(Dict) : Error cured while uploading file.
            key "code" - 1 is set if _max_size is exceeded
            key "code" - 2 is set if on some exceptional error
            key "error" contains addition error details
        size : Size of uploaded file. Actual size is available once upload is successful
    """

    def __init__(self, file_buffer, max_size, first_byte):
        self._buffer = file_buffer
        self._temp_file = None
        self._max_size = max_size + 1024
        self._error = None
        self._size = 1
        self._first_byte = first_byte

    # ------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------

    @property
    def name(self):
        return self._buffer.disposition_options['filename']

    @property
    def type(self):
        return self._buffer.type

    @property
    def size(self):
        return self._size

    @property
    def error(self):
        return self._error

    # ------------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------------

    def set_max_upload_size(self, size):
        """Set maximum number of bytes for file being uploaded

        Args:
            size (int): Number of bytes.
        """
        self._max_size = size + 1024

    def _set_error(self, error_data=None):
        if error_data:
            self._error = {
                'code': 2,
                'error': error_data
            }
        else:
            self._error = {
                'code': 1,
                'error': 'File size is more than ' + str(self._max_size) + ' bytes'
            }

    def uploadto(self, path):
        """Uploads file to given file path

        Args:
            path (str): Absolute path of file to be uploaded

        Returns:
            This method returns boolean - `True` on successful upload
            and if upload is unsuccessful then it returns `False` and sets error on failure.
        """

        fd, self._temp_file = tempfile.mkstemp()

        bytes_read_limit = 1024
        raw_bytes = self._first_byte

        try:
            with os.fdopen(fd, 'w+b') as tmp:
                while raw_bytes:
                    self._size = self._size + bytes_read_limit
                    if self._size >= self._max_size:
                        self._set_error()
                        self._deleteTempFile()
                        return False
                    tmp.write(raw_bytes)
                    raw_bytes = self._buffer.file.read(bytes_read_limit)
            self._moveTempFileTo(path)
        except Exception:
            self._deleteTempFile()
            exc_type, exc_value, exc_traceback = exc_info()
            error_data = {
                'type': exc_type,
                'value': exc_value,
                'traceback': exc_traceback
            }
            self._set_error(error_data)
            return False

        return True

    def _moveTempFileTo(self, path):
        os.rename(self._temp_file, path)
        self._temp_file = None
        self._size = os.path.getsize(path)

    def _deleteTempFile(self):
        if self._temp_file:
            os.remove(self._temp_file)
            self._temp_file = None

    def __del__(self):
        self._deleteTempFile()


# PERF: To avoid typos and improve storage space and speed over a dict.
class RequestOptions(object):
    """Defines a set of configurable request options.

    An instance of this class is exposed via :any:`API.req_options` for
    configuring certain :py:class:`~.Request` behaviors.

    Attributes:
        keep_blank_qs_values (bool): Set to ``True`` to keep query string
            fields even if they do not have a value (default ``False``).
            For comma-separated values, this option also determines
            whether or not empty elements in the parsed list are
            retained.

        auto_parse_form_urlencoded: Set to ``True`` in order to
            automatically consume the request stream and merge the
            results into the request's query string params when the
            request's content type is
            *application/x-www-form-urlencoded* (default ``False``).

            Enabling this option makes the form parameters accessible
            via :attr:`~.params`, :meth:`~.get_param`, etc.

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

        auto_parse_qs_csv: Set to ``False`` to treat commas in a query
            string value as literal characters, rather than as a comma-
            separated list (default ``True``). When this option is
            enabled, the value will be split on any non-percent-encoded
            commas. Disable this option when encoding lists as multiple
            occurrences of the same parameter, and when values may be
            encoded in alternative formats in which the comma character
            is significant.

        strip_url_path_trailing_slash: Set to ``False`` in order to
            retain a trailing slash, if present, at the end of the URL
            path (default ``True``). When this option is enabled,
            the URL path is normalized by stripping the trailing slash
            character. This lets the application define a single route
            to a resource for a path that may or may not end in a
            forward slash. However, this behavior can be problematic in
            certain cases, such as when working with authentication
            schemes that employ URL-based signatures.

        default_media_type (str): The default media-type to use when
            deserializing a response. This value is normally set to the media
            type provided when a :class:`falcon.API` is initialized; however,
            if created independently, this will default to the
            ``DEFAULT_MEDIA_TYPE`` specified by Falcon.

        media_handlers (Handlers): A dict-like object that allows you to
            configure the media-types that you would like to handle.
            By default, a handler is provided for the ``application/json``
            media type.

        file_max_upload_size: Maximum Number of bytes a single uploaded file
            may contain. Default value is 10 Mb. This value can be overriden
            by passing file_max_upload_size in falcon.API instance.
    """
    __slots__ = (
        'keep_blank_qs_values',
        'auto_parse_form_urlencoded',
        'auto_parse_qs_csv',
        'strip_url_path_trailing_slash',
        'default_media_type',
        'media_handlers',
        'file_max_upload_size',
    )

    def __init__(self):
        self.keep_blank_qs_values = False
        self.auto_parse_form_urlencoded = False
        self.auto_parse_qs_csv = True
        self.strip_url_path_trailing_slash = True
        self.default_media_type = DEFAULT_MEDIA_TYPE
        self.media_handlers = Handlers()
        self.file_max_upload_size = 1024 * 1024 * 10
