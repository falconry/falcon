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

from falcon.exceptions import *
from falcon import util
from falcon import request_helpers as helpers

DEFAULT_ERROR_LOG_FORMAT = ('{0:%Y-%m-%d %H:%M:%S} [FALCON] [ERROR]'
                            ' {1} {2}?{3} => {4}\n')


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
        'env',
        '_headers',
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
                the PEP-333 spec.

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
        if 'QUERY_STRING' in env:
            self.query_string = env['QUERY_STRING']
        else:
            self.query_string = ''

        # PERF: Don't parse it if we don't have to!
        if self.query_string:
            self._params = helpers.parse_query_string(self.query_string)
        else:
            self._params = {}

        self._headers = helpers.parse_headers(env)

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

    @property
    def client_accepts_json(self):
        """Return True if the Accept header indicates JSON support."""

        accept = self._get_header_by_wsgi_name('ACCEPT')
        return ((accept is not None) and
                (('application/json' in accept) or ('*/*' in accept)))

    @property
    def client_accepts_xml(self):
        """Return True if the Accept header indicates XML support."""

        accept = self._get_header_by_wsgi_name('ACCEPT')
        return ((accept is not None) and
                (('application/xml' in accept) or ('*/*' in accept)))

    @property
    def accept(self):
        """Value of the Accept header, or None if not found."""
        return self._get_header_by_wsgi_name('ACCEPT')

    @property
    def app(self):
        """Name of the WSGI app (if using WSGI's notion of virtual hosting)."""
        return self.env['SCRIPT_NAME']

    @property
    def auth(self):
        """Value of the Authorization header, or None if not found."""
        return self._get_header_by_wsgi_name('AUTHORIZATION')

    @property
    def content_length(self):
        """Value of the Content-Length header

        Returns:
            Value converted to an int, or None if missing.

        Raises:
            HTTPBadRequest: The header had a value, but it wasn't
                formatted correctly or was a negative number.
        """
        value = self._get_header_by_wsgi_name('CONTENT_LENGTH')
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

        # implicit return None

    @property
    def content_type(self):
        """Value of the Content-Type header, or None if not found."""
        return self._get_header_by_wsgi_name('CONTENT_TYPE')

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

        http_date = self._get_header_by_wsgi_name('DATE')
        try:
            return util.http_date_to_dt(http_date)
        except ValueError:
            msg = ('The value of the Date header could not be parsed. It '
                   'must be formatted according to RFC 1123.')
            raise InvalidHeaderValueError(msg)

    @property
    def expect(self):
        """Value of the Expect header, or None if missing."""
        return self._get_header_by_wsgi_name('EXPECT')

    @property
    def if_match(self):
        """Value of the If-Match header, or None if missing."""
        return self._get_header_by_wsgi_name('IF_MATCH')

    @property
    def if_none_match(self):
        """Value of the If-None-Match header, or None if missing."""
        return self._get_header_by_wsgi_name('IF_NONE_MATCH')

    @property
    def if_modified_since(self):
        """Value of the If-Modified-Since header, or None if missing."""
        return self._get_header_by_wsgi_name('IF_MODIFIED_SINCE')

    @property
    def if_unmodified_since(self):
        """Value of the If-Unmodified-Since header, or None if missing."""
        return self._get_header_by_wsgi_name('IF_UNMODIFIED_SINCE')

    @property
    def if_range(self):
        """Value of the If-Range header, or None if missing."""
        return self._get_header_by_wsgi_name('IF_RANGE')

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

        value = self._get_header_by_wsgi_name('RANGE')

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

     # implicit return None

    @property
    def uri(self):
        """The fully-qualified URI for the request."""

        # PERF: For small numbers of items, '+' is faster than ''.join(...)
        value = (self.protocol + '://' +
                 self.get_header('host') +
                 self.app +
                 self.path)

        if self.query_string:
            value = value + '?' + self.query_string

        return value

    url = uri
    """Alias for uri"""

    @property
    def relative_uri(self):
        """The path + query string portion of the full URI."""
        if self.query_string:
            return self.app + self.path + '?' + self.query_string

        return self.app + self.path

    @property
    def user_agent(self):
        """Value of the User-Agent string, or None if missing."""
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

        description = 'The "' + name + '" query parameter is required.'
        raise HTTPBadRequest('Missing query parameter', description)

    def get_param_as_int(self, name, required=False, min=None, max=None):
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

        Returns:
            The value of the param if it is found and can be converted to an
            integer. If the param is not found, returns None, unless
            unless required is True.

        Raises
            HTTPBadRequest: The param was not found in the request, even though
                it was required to be there. Also raised if the param's value
                falls outside the given interval, i.e., the value must be in
                the interval: min <= value <= max to avoid triggering an error.

        """

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in self._params:
            val = self._params[name]
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

            return val

        if not required:
            return None

        description = 'The "' + name + '" query parameter is required.'
        raise HTTPBadRequest('Missing query parameter', description)

    def get_param_as_bool(self, name, required=False):
        """Return the value of a query string parameter as a boolean

        Args:
            name: Parameter name, case-sensitive (e.g., 'limit')
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found or is not one of
                ['true', 'false'] (default False)

        Returns:
            The value of the param if it is found and can be converted to a
            boolean (must be in ['true', 'false']. If the param is not found,
            returns None unless required is True

        Raises
            HTTPBadRequest: The param was not found in the request, even though
                it was required to be there.

        """

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in self._params:
            val = self._params[name]
            if val == 'true':
                return True
            elif val == 'false':
                return False
            else:
                description = ('The value of the "' + name + '" query '
                               'parameter must be "true" or "false".')
                raise InvalidParamValueError(description)

        if not required:
            return None

        description = 'The "' + name + '" query parameter is required.'
        raise HTTPBadRequest('Missing query parameter', description)

    def get_param_as_list(self, name, transform=None, required=False):
        """Return the value of a query string parameter as a list

        Note that list items must be comma-separated.

        Args:
            name: Parameter name, case-sensitive (e.g., 'limit')
            transform: An optional transform function that takes as input
                each element in the list as a string and outputs a transformed
                element for inclusion in the list that will be returned.
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found or is not an
                integer (default False)

        Returns:
            The value of the param if it is found. Otherwise, returns None
            unless required is True.

        Raises
            HTTPBadRequest: The param was not found in the request, but was
                required.

        """

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in self._params:
            items = self._params[name].split(',')
            if transform is not None:
                try:
                    items = [transform(x) for x in items]
                except ValueError:
                    desc = ('The value of the "' + name + '" query parameter '
                            'is not formatted correctly.')
                    raise InvalidParamValueError(desc)

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
            return self._headers[name] or None
        except KeyError:
            return None
