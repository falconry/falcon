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

import six

from falcon.request_helpers import *
from falcon.exceptions import *

DEFAULT_ERROR_LOG_FORMAT = ('{0:%Y-%m-%d %H:%M:%S} [FALCON] [ERROR]'
                            ' {1} {2}?{3} => {4}\n')


class Request(object):
    """Represents a client's HTTP request

    Attributes:
        url: The fully-qualified request URL
        protocol: Will be either 'http' or 'https'.
        app: Name of the WSGI app (if using WSGI's notion of virtual hosting).
        method: HTTP method requested (e.g., GET, POST, etc.)
        path: Path portion of the request URL (not including query string).
        query_string: Query string portion of the request URL.
        stream: Stream-like object for reading the body of the request, if any.

        accept: Value of the Accept header, or None if not found.
        auth: Value of the Authorization header, or None if not found.
        content_length: Value of the Content-Length header, converted to an
            int, or None if missing or not an integer.
        content_type: Value of the Content-Type header, or None if not found.
        date: Value of the Date header, or None if missing.
        expect: Value of the Expect header, or None if missing.
        if_match: Value of the If-Match header, or None if missing.
        if_none_match: Value of the If-None-Match header, or None if missing.
        if_modified_since: Value of the If-Modified-Since header, or None if
            missing.
        if_unmodified_since: Value of the If-Unmodified-Since header, or None
            if missing.
        if_range: Value of the If-Range header, or None if missing.
        range: A 2-member tuple representing the value of the Range header, or
            None if missing. The two members correspond to first and last byte
            positions of the requested resource, inclusive. Negative indices
            indicate offset from the end of the resource, where -1 is the last
            byte, -2 is the second-to-last byte, and so forth.
        user_agent: Value of the User-Agent string, or None if not found.

    """

    __slots__ = (
        'app',
        '_headers',
        'method',
        '_params',
        'path',
        'protocol',
        'query_string',
        'stream',
        '_wsgierrors'
    )

    def __init__(self, env):
        """Initialize attributes based on a WSGI environment dict

        Note: Request is not meant to be instantiated directory by responders.

        Args:
            env: A WSGI environment dict passed in from the server. See also
                the PEP-333 spec.

        """

        self._wsgierrors = env['wsgi.errors']
        self.stream = env['wsgi.input']

        self.protocol = env['wsgi.url_scheme']
        self.app = env['SCRIPT_NAME']
        self.method = env['REQUEST_METHOD']
        self.path = env['PATH_INFO'] or '/'

        # QUERY_STRING isn't required to be in env, so let's check
        if 'QUERY_STRING' in env:
            self.query_string = query_string = env['QUERY_STRING']
        else:
            self.query_string = query_string = ''

        self._params = parse_query_string(query_string)
        self._headers = parse_headers(env)

    def log_error(self, message):
        """Log an error to wsgi.error

        Prepends timestamp and request info to message, and writes the
        result out to the WSGI server's error stream (wsgi.error).

        Args:
            message: A string describing the problem. If a byte-string and
                running under Python 2, the string is assumed to be encoded
                as UTF-8.

        """
        if not six.PY3 and isinstance(message, unicode):
            message = message.encode('utf-8')

        log_line = (
            DEFAULT_ERROR_LOG_FORMAT.
            format(datetime.now(), self.method, self.path,
                   self.query_string, message)
        )

        self._wsgierrors.write(log_line)

    def client_accepts_json(self):
        """Return True if the Accept header indicates JSON support"""

        accept = self.get_header('Accept')
        return ((accept is not None) and
                (('application/json' in accept) or ('*/*' in accept)))

    @property
    def url(self):
        return ''.join([
            self.protocol,
            '://',
            self.get_header('host'),
            self.app,
            self.path,
            self.query_string
        ])

    @property
    def accept(self):
        return self._get_header_by_wsgi_name('ACCEPT')

    @property
    def auth(self):
        return self._get_header_by_wsgi_name('AUTHORIZATION')

    @property
    def content_length(self):
        value = self._get_header_by_wsgi_name('CONTENT_LENGTH')
        if value is not None:
            try:
                return int(value)
            except ValueError:
                pass

        return None

    @property
    def content_type(self):
        return self._get_header_by_wsgi_name('CONTENT_TYPE')

    @property
    def date(self):
        return self._get_header_by_wsgi_name('DATE')

    @property
    def expect(self):
        return self._get_header_by_wsgi_name('EXPECT')

    @property
    def if_match(self):
        return self._get_header_by_wsgi_name('IF_MATCH')

    @property
    def if_none_match(self):
        return self._get_header_by_wsgi_name('IF_NONE_MATCH')

    @property
    def if_modified_since(self):
        return self._get_header_by_wsgi_name('IF_MODIFIED_SINCE')

    @property
    def if_unmodified_since(self):
        return self._get_header_by_wsgi_name('IF_UNMODIFIED_SINCE')

    @property
    def if_range(self):
        return self._get_header_by_wsgi_name('IF_RANGE')

    @property
    def range(self):
        value = self._get_header_by_wsgi_name('RANGE')
        if (value is None) or ('-' not in value):
            return None

        try:
            first, last = value.split('-')
        except ValueError:
            return None

        if first:
            if not last:
                last = -1

            return (int(first), int(last))

        elif last:
            return (-int(last), -1)

        return None

    @property
    def user_agent(self):
        return self._get_header_by_wsgi_name('USER_AGENT')

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
            return self._headers[name.upper().replace('-', '_')]
        except KeyError:
            if not required:
                return None

            description = 'The "' + name + '" header is required.'
            raise HTTPBadRequest('Missing header', description)

    def get_param(self, name, required=False):
        """Return the value of a query string parameter as a string

        Args:
            name: Parameter name, case-sensitive (e.g., 'sort')
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found (default False)

        Returns:
            The value of the param as a string, or None if param is not found
            and is not required.

        Raises:
            HTTPBadRequest: The param was not found in the request, but was
                required.

        """

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in self._params:
            return self._params[name]

        if not required:
            return None

        message = 'The "' + name + '" query parameter is required.'
        raise HTTPBadRequest('Missing query parameter', message)

    def get_param_as_int(self, name, required=False):
        """Return the value of a query string parameter as an int

        Args:
            name: Parameter name, case-sensitive (e.g., 'limit')
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found or is not an
                integer (default False)

        Returns:
            The value of the param if it is found and can be converted to an
            integer. Otherwise, returns None unless required is True.

        Raises
            HTTPBadRequest: The param was not found in the request, but was
                required.

        """

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in self._params:
            val = self._params[name]
            try:
                return int(val)
            except ValueError:
                pass

        if not required:
            return None

        message = 'The "' + name + '" query parameter is required.'
        raise HTTPBadRequest('Missing query parameter', message)

    def get_param_as_list(self, name, required=False):
        """Return the value of a query string parameter as an int

        Args:
            name: Parameter name, case-sensitive (e.g., 'limit')
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found or is not an
                integer (default False)

        Returns:
            The value of the param if it is found and can be converted to an
            integer. Otherwise, returns None unless required is True.

        Raises
            HTTPBadRequest: The param was not found in the request, but was
                required.

        """

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in self._params:
            return self._params[name].split(',')

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
            Value of the specified header, or None if not found

        """
        try:
            return self._headers[name]
        except KeyError:
            return None
