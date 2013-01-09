from falcon.request_helpers import *
from falcon.exceptions import *

class Request:
    __slots__ = (
        'app',
        'body',
        '_headers',
        'method',
        '_params',
        'path',
        'protocol',
        'query_string'
    )

    def __init__(self, env):
        self.app = env['SCRIPT_NAME']
        self.body = env['wsgi.input']
        self.method = env['REQUEST_METHOD']
        self.path = env['PATH_INFO'] or '/'
        self.protocol = env['wsgi.url_scheme']
        self.query_string = query_string = env['QUERY_STRING']
        self._params = parse_query_string(query_string)
        self._headers = parse_headers(env)

    def get_header(self, name, default=None, required=False):
        """Return a header value as a string

        name     -- Header name, case-insensitive (e.g., 'Content-Type')
        default  -- Value to return in case the header is not
                    found (default None)
        required -- Set to True to raise HttpBadRequest instead
                    of returning gracefully when the header is not
                    found (default False)

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

        name     -- Parameter name, case-sensitive (e.g., 'sort')
        default  -- Value to return in case the parameter is not
                    found in the query string (default None)
        required -- Set to True to raise HttpBadRequest instead
                    of returning gracefully when the parameter is not
                    found (default False)

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

        name     -- Parameter name, case-sensitive (e.g., 'limit')
        default  -- Value to return in case the parameter is not
                    found in the query string, or it is not an
                    integer (default None)
        required -- Set to True to raise HttpBadRequest instead
                    of returning gracefully when the parameter is not
                    found or is not an integer (default False)

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
