"""Defines the Request class.

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

from datetime import datetime

try:
    # NOTE(kgrifs): In Python 2.6 and 2.7, socket._fileobject is a
    # standard way of exposing a socket as a file-like object, and
    # is used by wsgiref for wsgi.input.
    import socket
    NativeStream = socket._fileobject
except AttributeError:  # pragma nocover
    # NOTE(kgriffs): In Python 3.3, wsgiref implements wsgi.input
    # using _io.BufferedReader which is an alias of io.BufferedReader
    import io
    NativeStream = io.BufferedReader

import mimeparse
import six

from falcon.exceptions import HTTPBadRequest
from falcon import util
from falcon.util import uri
from falcon import request_helpers as helpers


DEFAULT_ERROR_LOG_FORMAT = (u'{0:%Y-%m-%d %H:%M:%S} [FALCON] [ERROR]'
                            u' {1} {2}{3} => ')

TRUE_STRINGS = ('true', 'True', 'yes')
FALSE_STRINGS = ('false', 'False', 'no')


class InvalidHeaderValueError(HTTPBadRequest):
    def __init__(self, msg, href=None, href_text=None):
        super(InvalidHeaderValueError, self).__init__(
            'Invalid header value', msg, href=href, href_text=None)


class InvalidParamValueError(HTTPBadRequest):
    def __init__(self, msg, href=None, href_text=None):
        super(InvalidParamValueError, self).__init__(
            'Invalid query parameter', msg, href=href, href_text=None)


class Request(object):
    """Represents a client's HTTP request

    Attributes:
        method: HTTP method requested (e.g., GET, POST, etc.)
        path: Path portion of the request URL (not including query string).
        query_string: Query string portion of the request URL, without
            the preceding '?' character.
        stream: Stream-like object for reading the body of the request, if any.

    """

    __slots__ = (
        '_cached_headers',
        '_cached_uri',
        '_cached_relative_uri',
        'env',
        'method',
        '_params',
        'path',
        'query_string',
        'stream',
        '_wsgierrors'
    )

    def __init__(self, env):
        """Initialize attributes based on a WSGI environment dict

        Note: Request is not meant to be instantiated directory by responders.

        Args:
            env: A WSGI environment dict passed in from the server. See also
                the PEP-3333 spec.

        """
        self.env = env

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

        # QUERY_STRING isn't required to be in env, so let's check
        # PERF: if...in is faster than using env.get(...)
        if 'QUERY_STRING' in env and env['QUERY_STRING']:

            # TODO(kgriffs): Should this escape individual values instead
            # of the entire string? The way it is now, this:
            #
            #   x=ab%2Bcd%3D42%2C9
            #
            # becomes this:
            #
            #   x=ab+cd=42,9
            #
            self.query_string = uri.decode(env['QUERY_STRING'])

        else:
            self.query_string = six.text_type()

        # PERF: Don't parse it if we don't have to!
        if self.query_string:
            self._params = uri.parse_query_string(self.query_string)
        else:
            self._params = {}

        helpers.normalize_headers(env)
        self._cached_headers = {}

        self._cached_uri = None
        self._cached_relative_uri = None

        # NOTE(kgriffs): Wrap wsgi.input if needed to make read() more robust,
        # normalizing semantics between, e.g., gunicorn and wsgiref.
        if isinstance(self.stream, NativeStream):  # pragma: nocover
            # NOTE(kgriffs): coverage can't detect that this *is* actually
            # covered since the test that does so uses multiprocessing.
            self.stream = helpers.Body(self.stream, self.content_length)

    # TODO(kgriffs): Use the nocover pragma only for the six.PY3 if..else
    def log_error(self, message):  # pragma: no cover
        """Log an error to wsgi.error

        Prepends timestamp and request info to message, and writes the
        result out to the WSGI server's error stream (wsgi.error).

        Args:
            message: A string describing the problem. If a byte-string it is
                simply written out as-is. Unicode strings will be converted
                to UTF-8.

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
            if isinstance(message, unicode):
                message = message.encode('utf-8')

            self._wsgierrors.write(log_line.encode('utf-8'))
            self._wsgierrors.write(message + '\n')

    @property
    def client_accepts_json(self):
        """Return True if the Accept header indicates JSON support."""
        return self.client_accepts('application/json')

    @property
    def client_accepts_xml(self):
        """Return True if the Accept header indicates XML support."""
        return self.client_accepts('application/xml')

    def client_accepts(self, media_type):
        """Returns the client's preferred media type.

        Args:
            media_type: Media type to check

        Returns:
            True IFF the client has indicated in the Accept header that
            they accept at least one of the specified media types.
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
        """Returns the client's preferred media type given several choices.

        Args:
            media_types: One or more media types from which to choose the
                client's preferred type. This value MUST be an iterable
                collection of strings.

        Returns:
            The client's preferred media type, based on the Accept header,
            or None if the client does not accept any of the specified
            types.
        """

        try:
            # NOTE(kgriffs): best_match will return '' if no match is found
            preferred_type = mimeparse.best_match(media_types, self.accept)
        except ValueError:
            # Value for the accept header was not formatted correctly
            preferred_type = ''

        return (preferred_type if preferred_type else None)

    @property
    def accept(self):
        """Value of the Accept header, or */* if not found per RFC."""
        accept = self._get_header_by_wsgi_name('HTTP_ACCEPT')

        # NOTE(kgriffs): Per RFC, missing accept header is
        # equivalent to '*/*'
        return '*/*' if accept is None else accept

    @property
    def app(self):
        """Name of the WSGI app (if using WSGI's notion of virtual hosting)."""
        return self.env.get('SCRIPT_NAME', '')

    @property
    def auth(self):
        """Value of the Authorization header, or None if not found."""
        return self._get_header_by_wsgi_name('HTTP_AUTHORIZATION')

    @property
    def content_length(self):
        """Value of the Content-Length header

        Returns:
            Value converted to an int, or None if missing.

        Raises:
            HTTPBadRequest: The header had a value, but it wasn't
                formatted correctly or was a negative number.
        """
        value = self._get_header_by_wsgi_name('HTTP_CONTENT_LENGTH')
        if value:
            try:
                value_as_int = int(value)
            except ValueError:
                msg = ('The value of the content-length header must be '
                       'a number.')
                raise InvalidHeaderValueError(msg)

            if value_as_int < 0:
                msg = ('The value of the content-length header must be '
                       'a positive number.')
                raise InvalidHeaderValueError(msg)
            else:
                return value_as_int

        return None

    @property
    def content_type(self):
        """Value of the Content-Type header, or None if not found."""
        return self._get_header_by_wsgi_name('HTTP_CONTENT_TYPE')

    @property
    def date(self):
        """Value of the Date header, converted to a datetime instance.

        Returns:
            An instance of datetime.datetime representing the value of
            the Date header, or None if the Date header is not present
            in the request.

        Raises:
            HTTPBadRequest: The date value could not be parsed, likely
                because it does not confrom to RFC 1123.

        """

        http_date = self._get_header_by_wsgi_name('HTTP_DATE')
        try:
            return util.http_date_to_dt(http_date)
        except ValueError:
            msg = ('The value of the Date header could not be parsed. It '
                   'must be formatted according to RFC 1123.')
            raise InvalidHeaderValueError(msg)

    @property
    def expect(self):
        """Value of the Expect header, or None if missing."""
        return self._get_header_by_wsgi_name('HTTP_EXPECT')

    @property
    def if_match(self):
        """Value of the If-Match header, or None if missing."""
        return self._get_header_by_wsgi_name('HTTP_IF_MATCH')

    @property
    def if_none_match(self):
        """Value of the If-None-Match header, or None if missing."""
        return self._get_header_by_wsgi_name('HTTP_IF_NONE_MATCH')

    @property
    def if_modified_since(self):
        """Value of the If-Modified-Since header, or None if missing."""
        return self._get_header_by_wsgi_name('HTTP_IF_MODIFIED_SINCE')

    @property
    def if_unmodified_since(self):
        """Value of the If-Unmodified-Since header, or None if missing."""
        return self._get_header_by_wsgi_name('HTTP_IF_UNMODIFIED_SINCE')

    @property
    def if_range(self):
        """Value of the If-Range header, or None if missing."""
        return self._get_header_by_wsgi_name('HTTP_IF_RANGE')

    @property
    def protocol(self):
        """Will be either 'http' or 'https'."""
        return self.env['wsgi.url_scheme']

    @property
    def range(self):
        """A 2-member tuple representing the value of the Range header.

        The two members correspond to first and last byte positions of the
        requested resource, inclusive. Negative indices indicate offset
        from the end of the resource, where -1 is the last byte, -2 is the
        second-to-last byte, and so forth.

        Only continous ranges are supported (e.g., "bytes=0-0,-1" would
        result in an HTTPBadRequest exception.)

        Returns:
            Parse range value, or None if the header is not present.

        Raises:
            HTTPBadRequest: The header had a value, but it wasn't
                formatted correctly.
        """

        value = self._get_header_by_wsgi_name('HTTP_RANGE')

        if value:
            if ',' in value:
                raise InvalidHeaderValueError('Only continuous byte ranges '
                                              'are supported.')

            try:
                first, last = value.split('-')

                if first:
                    return (int(first), int(last or -1))
                elif last:
                    return (-int(last), -1)
                else:
                    raise InvalidHeaderValueError(
                        'Range value is missing offsets')

            except ValueError:
                href = 'http://goo.gl/zZ6Ey'
                href_text = 'HTTP/1.1 Range Requests'
                raise InvalidHeaderValueError('Range string must be formatted '
                                              'according to RFC 2616.',
                                              href=href,
                                              href_text=href_text)

        return None

    @property
    def uri(self):
        """The fully-qualified URI for the request."""

        if self._cached_uri is None:
            # PERF: For small numbers of items, '+' is faster
            # than ''.join(...). Concatenation is also generally
            # faster than formatting.
            value = (self.protocol + '://' +
                     self.get_header('host') +
                     self.app +
                     self.path)

            if self.query_string:
                value = value + '?' + self.query_string

            self._cached_uri = value

        return self._cached_uri

    url = uri
    """Alias for uri"""

    @property
    def relative_uri(self):
        """The path + query string portion of the full URI."""

        if self._cached_relative_uri is None:
            if self.query_string:
                self._cached_relative_uri = (self.app + self.path + '?' +
                                             self.query_string)
            else:
                self._cached_relative_uri = self.app + self.path

        return self._cached_relative_uri

    @property
    def user_agent(self):
        """Value of the User-Agent string, or None if missing."""
        return self._get_header_by_wsgi_name('HTTP_USER_AGENT')

    @property
    def headers(self):
        """Get raw HTTP headers

        Build a temporary dictionary of dash-separated HTTP headers,
        which can be used as a whole, like, to perform an HTTP request.

        If you want to lookup a header, please use `get_header` instead.

        Returns:
            A new dictionary of HTTP headers.

        """

        # NOTE(kgriffs: First time here will cache the dict so all we
        # have to do is clone it in the future.
        if not self._cached_headers:
            headers = self._cached_headers

            env = self.env
            for name, value in env.items():
                if name.startswith('HTTP_'):
                    # NOTE(kgriffs): Don't take the time to fix the case
                    # since headers are supposed to be case-insensitive
                    # anyway.
                    headers[name[5:].replace('_', '-')] = value

        return self._cached_headers.copy()

    def get_header(self, name, required=False):
        """Return a header value as a string

        Args:
            name: Header name, case-insensitive (e.g., 'Content-Type')
            required: Set to True to raise HttpBadRequest instead
              of returning gracefully when the header is not found
              (default False)

        Returns:
            The value of the specified header if it exists, or None if the
            header is not found and is not required.

        Raises:
            HTTPBadRequest: The header was not found in the request, but
                it was required.

        """

        # Use try..except to optimize for the header existing in most cases
        try:
            # Don't take the time to cache beforehand, using HTTP naming.
            # This will be faster, assuming that most headers are looked
            # up only once, and not all headers will be requested.
            return self.env['HTTP_' + name.upper().replace('-', '_')]
        except KeyError:
            if not required:
                return None

            description = 'The "' + name + '" header is required.'
            raise HTTPBadRequest('Missing header', description)

    def get_param(self, name, required=False, store=None):
        """Return the value of a query string parameter as a string

        Args:
            name: Parameter name, case-sensitive (e.g., 'sort')
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found (default False)
            store: A dict-like object in which to place the value of the
                param, but only if the param is found.

        Returns:
            The value of the param as a string, or None if param is not found
            and is not required.

        Raises:
            HTTPBadRequest: The param was not found in the request, but was
                required.

        """

        params = self._params

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            if store is not None:
                store[name] = params[name]

            return params[name]

        if not required:
            return None

        description = 'The "' + name + '" query parameter is required.'
        raise HTTPBadRequest('Missing query parameter', description)

    def get_param_as_int(self, name,
                         required=False, min=None, max=None, store=None):
        """Return the value of a query string parameter as an int

        Args:
            name: Parameter name, case-sensitive (e.g., 'limit')
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found or is not an
                integer (default False)
            min: Set to the minimum value allowed for this param. If the param
                is found and it is less than min, an HTTPError is raised.
            max: Set to the maximum value allowed for this param. If the param
                is found and its value is greater than max, an HTTPError is
                raised.
            store: A dict-like object in which to place the value of the
                param, but only if the param is found (default None)

        Returns:
            The value of the param if it is found and can be converted to an
            integer. If the param is not found, returns None, unless required
            is True.

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
            try:
                val = int(val)
            except ValueError:
                description = ('The value of the "' + name + '" query '
                               'parameter must be an integer.')
                raise InvalidParamValueError(description)

            if min is not None and val < min:
                description = ('The value of the "' + name + '" query '
                               'parameter must be at least %d') % min
                raise InvalidHeaderValueError(description)

            if max is not None and max < val:
                description = ('The value of the "' + name + '" query '
                               'parameter may not exceed %d') % max
                raise InvalidHeaderValueError(description)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return None

        description = 'The "' + name + '" query parameter is required.'
        raise HTTPBadRequest('Missing query parameter', description)

    def get_param_as_bool(self, name, required=False, store=None):
        """Return the value of a query string parameter as a boolean

        The following bool-ish strings are supported:

            True: ('true', 'True', 'yes')
            False: ('false', 'False', 'no')

        Args:
            name: Parameter name, case-sensitive (e.g., 'limit')
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found or is not a
                recognized bool-ish string (default False).
            store: A dict-like object in which to place the value of the
                param, but only if the param is found (default None)

        Returns:
            The value of the param if it is found and can be converted to a
            boolean. If the param is not found,
            returns None unless required is True

        Raises
            HTTPBadRequest: The param was not found in the request, even though
                it was required to be there.

        """

        params = self._params

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            val = params[name]
            if val in TRUE_STRINGS:
                val = True
            elif val in FALSE_STRINGS:
                val = False
            else:
                description = ('The value of the "' + name + '" query '
                               'parameter must be "true" or "false".')
                raise InvalidParamValueError(description)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return None

        description = 'The "' + name + '" query parameter is required.'
        raise HTTPBadRequest('Missing query parameter', description)

    def get_param_as_list(self, name,
                          transform=None, required=False, store=None):
        """Return the value of a query string parameter as a list

        Note that list items must be comma-separated.

        Args:
            name: Parameter name, case-sensitive (e.g., 'limit')
            transform: An optional transform function that takes as input
                each element in the list as a string and outputs a transformed
                element for inclusion in the list that will be returned. For
                example, passing the int function will transform list items
                into numbers.
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found or is not an
                integer (default False)
            store: A dict-like object in which to place the value of the
                param, but only if the param is found (default None)

        Returns:
            The value of the param if it is found. Otherwise, returns None
            unless required is True. for partial lists, None will be returned
            as a placeholder. For example:

                things=1,,3

            would be returned as:

                ['1', None, '3']

            while this:

                things=,,,

            would just be retured as:

                [None, None, None, None]

        Raises
            HTTPBadRequest: The param was not found in the request, but was
                required.
        """

        params = self._params

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            items = params[name].split(',')

            # PERF(kgriffs): Use if-else rather than a DRY approach
            # that sets transform to a passthrough function; avoids
            # function calling overhead.
            if transform is None:
                items = [i if i != '' else None
                         for i in items]
            else:
                try:
                    items = [transform(i) if i != '' else None
                             for i in items]
                except ValueError:
                    desc = ('The value of the "' + name + '" query parameter '
                            'is not formatted correctly.')
                    raise InvalidParamValueError(desc)

            if store is not None:
                store[name] = items

            return items

        if not required:
            return None

        raise HTTPBadRequest('Missing query parameter',
                             'The "' + name + '" query parameter is required.')

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_header_by_wsgi_name(self, name):
        """Looks up a header, assuming name is already UPPERCASE_UNDERSCORE

        Args:
            name: Name of the header, already uppercased, and underscored

        Returns:
            Value of the specified header, or None if the header was not
            found. Also returns None if the value of the header was blank.

        """
        try:
            return self.env[name] or None
        except KeyError:
            return None
