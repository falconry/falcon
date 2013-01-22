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

import sys
from datetime import datetime

from falcon.request_helpers import *
from falcon.exceptions import *


class Request(object):
    """Represents a client's HTTP request"""

    __slots__ = (
        'app',
        'body',
        '_headers',
        'method',
        '_params',
        'path',
        'protocol',
        'query_string',
        '_wsgierrors'
    )

    def __init__(self, env):
        """Initialize attributes based on a WSGI environment dict

        Note: Request is not meant to be instantiated directory by responders.

        Args:
            env: A WSGI environment dict passed in from the server. See also
                the PEP-333 spec.

        """

        self.app = env['SCRIPT_NAME']
        self.body = env['wsgi.input']
        self.method = env['REQUEST_METHOD']
        self.path = env['PATH_INFO'] or '/'
        self.protocol = env['wsgi.url_scheme']
        self.query_string = query_string = env['QUERY_STRING']
        self._params = parse_query_string(query_string)
        self._headers = parse_headers(env)
        self._wsgierrors = env['wsgi.errors']

    def log_error(self, message):
        """Log an error to wsgi.error

        Prepends timestamp and request info to message, and writes the result
        out to the WSGI server's error stream (wsgi.error).

        Args:
            message: A string describing the problem. If a byte-string and
                running under Python 2, the string is assumed to be encoded
                as UTF-8.

        """

        if sys.version_info[0] == 2 and isinstance(message, str):
            unicode_message = message.decode('utf-8')
        else:
            unicode_message = message

        log_line = (
            u'{0:%Y-%m-%d %H:%M:%S} [FALCON] [ERROR] {1} {2}?{3} => {4}\n'.
            format(datetime.now(), self.method, self.path, self.query_string,
                   unicode_message)
        )

        self._wsgierrors.write(log_line)

    def client_accepts_json(self):
        """Return True if the Accept header indicates JSON support"""

        accept = self.get_header('Accept')
        if accept is not None:
            return ('application/json' in accept) or ('*/*' in accept)

        return False

    def get_header(self, name, default=None, required=False):
        """Return a header value as a string

        Args:
            name: Header name, case-insensitive (e.g., 'Content-Type')
            default: Value to return in case the header is not
              found (default None)
            required: Set to True to raise HttpBadRequest instead
              of returning gracefully when the header is not found
              (default False)

        """

        # Use try..except to optimize for the header existing in most cases
        try:
            # Don't take the time to cache beforehand, using HTTP naming.
            # This will be faster, assuming that most headers are looked
            # up only once, and not all headers will be requested.
            return self._headers[name.upper().replace('-', '_')]
        except KeyError:
            if not required:
                return default

            raise HTTPBadRequest('Missing header',
                                 'The "' + name + '" header is required.')

    def get_param(self, name, default=None, required=False):
        """Return the value of a query string parameter as a string

        Args:
            name: Parameter name, case-sensitive (e.g., 'sort')
            default: Value to return in case the parameter is not found in the
                query string (default None)
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found (default False)

        Returns:
            The value of the param as a byte string, or the default value if
            param is not found and is not required.

        Raises
            HTTPBadRequest: The param was not found in the request, but was
                required.

        """

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in self._params:
            return self._params[name]

        if not required:
            return default

        raise HTTPBadRequest('Missing query parameter',
                             'The "' + name + '" query parameter is required.')

    def get_param_as_int(self, name, default=None, required=False):
        """Return the value of a query string parameter as an int

        Args:
            name: Parameter name, case-sensitive (e.g., 'limit')
            default: Value to return in case the parameter is not found in the
                query string, or it is not an integer (default None)
            required: Set to True to raise HTTPBadRequest instead of returning
                gracefully when the parameter is not found or is not an
                integer (default False)

        Returns:
            The value of the param if it is found and can be converted to an
            integer. Otherwise, returns the default value unless required is
            True.

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
            return default

        raise HTTPBadRequest('Missing query parameter',
                             'The "' + name + '" query parameter is required.')
