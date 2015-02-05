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

from datetime import datetime

try:
    # NOTE(kgrifs): In Python 2.6 and 2.7, socket._fileobject is a
    # standard way of exposing a socket as a file-like object, and
    # is used by wsgiref for wsgi.input.
    import socket
    NativeStream = socket._fileobject  # pylint: disable=E1101
except AttributeError:  # pragma nocover
    # NOTE(kgriffs): In Python 3.3, wsgiref implements wsgi.input
    # using _io.BufferedReader which is an alias of io.BufferedReader
    import io
    NativeStream = io.BufferedReader

import mimeparse
import six

from falcon.errors import *
from falcon import util
from falcon.util import uri
from falcon import request_helpers as helpers


DEFAULT_ERROR_LOG_FORMAT = (u'{0:%Y-%m-%d %H:%M:%S} [FALCON] [ERROR]'
                            u' {1} {2}{3} => ')

TRUE_STRINGS = ('true', 'True', 'yes')
FALSE_STRINGS = ('false', 'False', 'no')
WSGI_CONTENT_HEADERS = ('CONTENT_TYPE', 'CONTENT_LENGTH')


_maybe_wrap_wsgi_stream = True


class Request(object):
    """Represents a client's HTTP request.

    Note:
        `Request` is not meant to be instantiated directly by responders.

    Args:
        env (dict): A WSGI environment dict passed in from the server. See
            also PEP-3333.
        options (dict): Set of global options passed from the API handler.

    Attributes:
        protocol (str): Either 'http' or 'https'.
        method (str): HTTP method requested (e.g., 'GET', 'POST', etc.)
        host (str): Hostname requested by the client
        subdomain (str): Leftmost (i.e., most specific) subdomain from the
            hostname. If only a single domain name is given, `subdomain`
            will be ``None``.

            Note:
                If the hostname in the request is an IP address, the value
                for `subdomain` is undefined.

        user_agent (str): Value of the User-Agent header, or ``None`` if the
            header is missing.
        app (str): Name of the WSGI app (if using WSGI's notion of virtual
            hosting).
        env (dict): Reference to the WSGI environ ``dict`` passed in from the
            server. See also PEP-3333.
        context (dict): Dictionary to hold any data about the request which is
            specific to your app (e.g. session object). Falcon itself will
            not interact with this attribute after it has been initialized.
        context_type (class): Class variable that determines the
            factory or type to use for initializing the
            `context` attribute. By default, the framework will
            instantiate standard
            ``dict`` objects. However, You may override this behavior
            by creating a custom child class of ``falcon.Request``, and
            then passing that new class to `falcon.API()` by way of the
            latter's `request_type` parameter.
        uri (str): The fully-qualified URI for the request.
        url (str): alias for `uri`.
        relative_uri (str): The path + query string portion of the full URI.
        path (str): Path portion of the request URL (not including query
            string).
        query_string (str): Query string portion of the request URL, without
            the preceding '?' character.
        accept (str): Value of the Accept header, or '*/*' if the header is
            missing.
        auth (str): Value of the Authorization header, or ``None`` if the
            header is missing.
        client_accepts_json (bool): ``True`` if the Accept header indicates
            that the client is willing to receive JSON, otherwise ``False``.
        client_accepts_msgpack (bool): ``True`` if the Accept header indicates
            that the client is willing to receive MessagePack, otherwise
            ``False``.
        client_accepts_xml (bool): ``True`` if the Accept header indicates that
            the client is willing to receive XML, otherwise ``False``.
        content_type (str): Value of the Content-Type header, or ``None`` if
            the header is missing.
        content_length (int): Value of the Content-Length header converted
            to an ``int``, or ``None`` if the header is missing.
        stream: File-like object for reading the body of the request, if any.

            Note:
                If an HTML form is POSTed to the API using the
                *application/x-www-form-urlencoded* media type, Falcon
                will consume `stream` in order to parse the parameters
                and merge them into the query string parameters. In this
                case, the stream will be left at EOF.

                Note also that the character encoding for fields, before
                percent-encoding non-ASCII bytes, is assumed to be
                UTF-8. The special `_charset_` field is ignored if present.

                Falcon expects form-encoded request bodies to be
                encoded according to the standard W3C algorithm (see
                also http://goo.gl/6rlcux).

        date (datetime): Value of the Date header, converted to a
            ``datetime`` instance. The header value is assumed to
            conform to RFC 1123.
        expect (str): Value of the Expect header, or ``None`` if the
            header is missing.
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
        if_match (str): Value of the If-Match header, or ``None`` if the
            header is missing.
        if_none_match (str): Value of the If-None-Match header, or ``None``
            if the header is missing.
        if_modified_since (str): Value of the If-Modified-Since header, or
            ``None`` if the header is missing.
        if_unmodified_since (str): Value of the If-Unmodified-Sinc header,
            or ``None`` if the header is missing.
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

        options (dict): Set of global options passed from the API handler.
    """

    __slots__ = (
        '_cached_headers',
        '_cached_uri',
        '_cached_relative_uri',
        'content_type',
        'env',
        'method',
        '_params',
        'path',
        'query_string',
        'stream',
        'context',
        '_wsgierrors',
        'options',
    )

    # Allow child classes to override this
    context_type = None

    def __init__(self, env, options=None):
        global _maybe_wrap_wsgi_stream

        self.env = env
        self.options = options if options else RequestOptions()

        if self.context_type is None:
            # Literal syntax is more efficient than using dict()
            self.context = {}
        else:
            # pylint will detect this as not-callable because it only sees the
            # declaration of None, not whatever type a subclass may have set.
            self.context = self.context_type()  # pylint: disable=not-callable

        self._wsgierrors = env['wsgi.errors']
        self.stream = env['wsgi.input']
        self.method = env['REQUEST_METHOD']

        # Normalize path
        path = env['PATH_INFO']
        if path:
            if len(path) != 1 and path.endswith('/'):
                self.path = path[:-1]
            else:
                self.path = path
        else:
            self.path = '/'

        self._params = {}

        # PERF(kgriffs): if...in is faster than using env.get(...)
        if 'QUERY_STRING' in env:
            query_str = env['QUERY_STRING']

            if query_str:
                self.query_string = uri.decode(query_str)
                self._params = uri.parse_query_string(
                    self.query_string,
                    keep_blank_qs_values=self.options.keep_blank_qs_values,
                )
            else:
                self.query_string = six.text_type()

        else:
            self.query_string = six.text_type()

        self._cached_headers = None
        self._cached_uri = None
        self._cached_relative_uri = None

        try:
            self.content_type = self.env['CONTENT_TYPE']
        except KeyError:
            self.content_type = None

        # NOTE(kgriffs): Wrap wsgi.input if needed to make read() more robust,
        # normalizing semantics between, e.g., gunicorn and wsgiref.
        if _maybe_wrap_wsgi_stream:
            if isinstance(self.stream, NativeStream):
                # NOTE(kgriffs): This is covered by tests, it's just that
                # coverage can't figure this out for some reason (TBD).
                self._wrap_stream()  # pragma nocover
            else:
                # PERF(kgriffs): If self.stream does not need to be wrapped
                # this time, it never needs to be wrapped since the server
                # will continue using the same type for wsgi.input.
                _maybe_wrap_wsgi_stream = False

        # PERF(kgriffs): Technically, we should spend a few more
        # cycles and parse the content type for real, but
        # this heuristic will work virtually all the time.
        if (self.content_type is not None and
                'application/x-www-form-urlencoded' in self.content_type):
            self._parse_form_urlencoded()

    # ------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------

    user_agent = helpers.header_property('HTTP_USER_AGENT')
    auth = helpers.header_property('HTTP_AUTHORIZATION')

    expect = helpers.header_property('HTTP_EXPECT')

    if_match = helpers.header_property('HTTP_IF_MATCH')
    if_none_match = helpers.header_property('HTTP_IF_NONE_MATCH')
    if_modified_since = helpers.header_property('HTTP_IF_MODIFIED_SINCE')
    if_unmodified_since = helpers.header_property('HTTP_IF_UNMODIFIED_SINCE')
    if_range = helpers.header_property('HTTP_IF_RANGE')

    @property
    def client_accepts_json(self):
        return self.client_accepts('application/json')

    @property
    def client_accepts_msgpack(self):
        return self.client_accepts('application/x-msgpack')

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
            raise HTTPInvalidHeader(msg, 'Content-Length')

        if value_as_int < 0:
            msg = 'The value of the header must be a positive number.'
            raise HTTPInvalidHeader(msg, 'Content-Length')

        return value_as_int

    @property
    def date(self):
        try:
            http_date = self.env['HTTP_DATE']
        except KeyError:
            return None

        try:
            return util.http_date_to_dt(http_date)
        except ValueError:
            msg = ('It must be formatted according to RFC 1123.')
            raise HTTPInvalidHeader(msg, 'Date')

    @property
    def range(self):
        try:
            value = self.env['HTTP_RANGE']
            if value.startswith('bytes='):
                value = value[6:]
        except KeyError:
            return None

        if ',' in value:
            msg = 'The value must be a continuous byte range.'
            raise HTTPInvalidHeader(msg, 'Range')

        try:
            first, sep, last = value.partition('-')

            if not sep:
                raise ValueError()

            if first:
                return (int(first), int(last or -1))
            elif last:
                return (-int(last), -1)
            else:
                msg = 'The byte offsets are missing.'
                raise HTTPInvalidHeader(msg, 'Range')

        except ValueError:
            href = 'http://goo.gl/zZ6Ey'
            href_text = 'HTTP/1.1 Range Requests'
            msg = ('It must be a byte range formatted according to RFC 2616.')
            raise HTTPInvalidHeader(msg, 'Range', href=href,
                                    href_text=href_text)

    @property
    def app(self):
        return self.env.get('SCRIPT_NAME', '')

    @property
    def protocol(self):
        return self.env['wsgi.url_scheme']

    @property
    def uri(self):
        if self._cached_uri is None:
            env = self.env
            protocol = env['wsgi.url_scheme']

            # NOTE(kgriffs): According to PEP-3333 we should first
            # try to use the Host header if present.
            #
            # PERF(kgriffs): try..except is faster than .get
            try:
                host = env['HTTP_HOST']
            except KeyError:
                host = env['SERVER_NAME']
                port = env['SERVER_PORT']

                if protocol == 'https':
                    if port != '443':
                        host += ':' + port
                else:
                    if port != '80':
                        host += ':' + port

            # PERF: For small numbers of items, '+' is faster
            # than ''.join(...). Concatenation is also generally
            # faster than formatting.
            value = (protocol + '://' +
                     host +
                     self.app +
                     self.path)

            if self.query_string:
                value = value + '?' + self.query_string

            self._cached_uri = value

        return self._cached_uri

    url = uri

    @property
    def host(self):
        try:
            # NOTE(kgriffs): Prefer the host header; the web server
            # isn't supposed to mess with it, so it should be what
            # the client actually sent.
            host_header = self.env['HTTP_HOST']
            host, port = uri.parse_host(host_header)
        except KeyError:
            # PERF(kgriffs): According to PEP-3333, this header
            # will always be present.
            host = self.env['SERVER_NAME']

        return host

    @property
    def subdomain(self):
        # PERF(kgriffs): .partition is slightly faster than .split
        subdomain, sep, remainder = self.host.partition('.')
        return subdomain if sep else None

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

    # ------------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------------

    def client_accepts(self, media_type):
        """Determines whether or not the client accepts a given media type.

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
        """Returns the client's preferred media type, given several choices.

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

    def get_header(self, name, required=False):
        """Return a raw header value as a string.

        Args:
            name (str): Header name, case-insensitive (e.g., 'Content-Type')
            required (bool, optional): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning gracefully when the
                header is not found (default ``False``).

        Returns:
            str: The value of the specified header if it exists, or ``None`` if
                the header is not found and is not required.

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
                return None

            raise HTTPMissingParam(name)

    def get_param(self, name, required=False, store=None):
        """Return the raw value of a query string parameter as a string.

        Note:
            If an HTML form is POSTed to the API using the
            *application/x-www-form-urlencoded* media type, the
            parameters from the request body will be merged into
            the query string parameters.

            If a key appears more than once in the form data, one of the
            values will be returned as a string, but it is undefined which
            one. Use `req.get_param_as_list()` to retrieve all the values.

        Note:
            Similar to the way multiple keys in form data is handled,
            if a query parameter is assigned a comma-separated list of
            values (e.g., 'foo=a,b,c'), only one of those values will be
            returned, and it is undefined which one. Use
            `req.get_param_as_list()` to retrieve all the values.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'sort').
            required (bool, optional): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found (default ``False``).
            store (dict, optional): A ``dict``-like object in which to place
                the value of the param, but only if the param is present.

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
            return None

        raise HTTPMissingParam(name)

    def get_param_as_int(self, name,
                         required=False, min=None, max=None, store=None):
        """Return the value of a query string parameter as an int.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'limit').
            required (bool, optional): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found or is not an integer (default
                ``False``).
            min (int, optional): Set to the minimum value allowed for this
                param. If the param is found and it is less than min, an
                ``HTTPError`` is raised.
            max (int, optional): Set to the maximum value allowed for this
                param. If the param is found and its value is greater than
                max, an ``HTTPError`` is raised.
            store (dict, optional): A ``dict``-like object in which to place
                the value of the param, but only if the param is found
                (default ``None``).

        Returns:
            int: The value of the param if it is found and can be converted to
                an integer. If the param is not found, returns ``None``, unless
                `required` is ``True``.

        Raises
            HTTPBadRequest: The param was not found in the request, even though
                it was required to be there. Also raised if the param's value
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
                raise HTTPInvalidParam(msg, name)

            if min is not None and val < min:
                msg = 'The value must be at least ' + str(min)
                raise HTTPInvalidParam(msg, name)

            if max is not None and max < val:
                msg = 'The value may not exceed ' + str(max)
                raise HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return None

        raise HTTPMissingParam(name)

    def get_param_as_bool(self, name, required=False, store=None,
                          blank_as_true=False):
        """Return the value of a query string parameter as a boolean

        The following boolean strings are supported::

            TRUE_STRINGS = ('true', 'True', 'yes')
            FALSE_STRINGS = ('false', 'False', 'no')

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'detailed').
            required (bool, optional): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found or is not a recognized boolean
                string (default ``False``).
            store (dict, optional): A ``dict``-like object in which to place
                the value of the param, but only if the param is found (default
                ``None``).
            blank_as_true (bool): If ``True``, an empty string value will be
                treated as ``True``. Normally empty strings are ignored; if
                you would like to recognize such parameters, you must set the
                `keep_blank_qs_values` request option to ``True``. Request
                options are set globally for each instance of ``falcon.API``
                through the `req_options` attribute.

        Returns:
            bool: The value of the param if it is found and can be converted
                to a ``bool``. If the param is not found, returns ``None``
                unless required is ``True``.

        Raises:
            HTTPBadRequest: A required param is missing from the request.

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
                raise HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return None

        raise HTTPMissingParam(name)

    def get_param_as_list(self, name,
                          transform=None, required=False, store=None):
        """Return the value of a query string parameter as a list.

        List items must be comma-separated or must be provided
        as multiple instances of the same param in the query string
        ala *application/x-www-form-urlencoded*.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'ids').
            transform (callable, optional): An optional transform function
                that takes as input each element in the list as a ``str`` and
                outputs a transformed element for inclusion in the list that
                will be returned. For example, passing ``int`` will
                transform list items into numbers.
            required (bool, optional): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found (default ``False``).
            store (dict, optional): A ``dict``-like object in which to place
                the value of the param, but only if the param is found (default
                ``None``).

        Returns:
            list: The value of the param if it is found. Otherwise, returns
            ``None`` unless required is True. Empty list elements will be
            discarded. For example a query string containing this::

                things=1,,3

            or a query string containing this::

                things=1&things=&things=3

            would both result in::

                ['1', '3']

        Raises:
            HTTPBadRequest: A required param is missing from the request.
            HTTPInvalidParam: A tranform function raised an instance of
                ``ValueError``.

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
                    raise HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = items

            return items

        if not required:
            return None

        raise HTTPMissingParam(name)

    # TODO(kgriffs): Use the nocover pragma only for the six.PY3 if..else
    def log_error(self, message):  # pragma: no cover
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
            format(datetime.now(), self.method, self.path,
                   query_string_formatted)
        )

        if six.PY3:
            self._wsgierrors.write(log_line + message + '\n')
        else:
            if isinstance(message, unicode):  # pylint: disable=E0602
                message = message.encode('utf-8')

            self._wsgierrors.write(log_line.encode('utf-8'))
            self._wsgierrors.write(message + '\n')

    # ------------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------------

    def _wrap_stream(self):  # pragma nocover
        try:
            # NOTE(kgriffs): We can only add the wrapper if the
            # content-length header was provided.
            if self.content_length is not None:
                self.stream = helpers.Body(self.stream, self.content_length)

        except HTTPInvalidHeader:
            # NOTE(kgriffs): The content-length header was specified,
            # but it had an invalid value.
            pass

    def _parse_form_urlencoded(self):
        # NOTE(kgriffs): This assumes self.stream has been patched
        # above in the case of wsgiref, so that self.content_length
        # is not needed. Normally we just avoid accessing
        # self.content_length, because it is a little expensive
        # to call. We could cache self.content_length, but the
        # overhead to do that won't usually be helpful, since
        # content length will only ever be read once per
        # request in most cases.
        body = self.stream.read()

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
            extra_params = uri.parse_query_string(
                uri.decode(body),
                keep_blank_qs_values=self.options.keep_blank_qs_values,
            )

            self._params.update(extra_params)


# PERF: To avoid typos and improve storage space and speed over a dict.
class RequestOptions(object):
    """This class is a container for ``Request`` options.

    Attributes:
        keep_blank_qs_values (bool): Set to ``True`` in order to retain
            blank values in query string parameters (default ``False``).

    """
    __slots__ = (
        'keep_blank_qs_values',
    )

    def __init__(self):
        self.keep_blank_qs_values = False
