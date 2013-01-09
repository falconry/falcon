from falcon.request_helpers import *


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

    def try_get_header(self, name, default=None):
        """Return a header value as a string

        name -- Header name, case-insensitive (e.g., 'Content-Type')
        default -- Value to return in case the header is not found

        """

        # Use try..except to optimize for the header existing in most cases
        try:
            # Don't take the time to cache beforehand, using HTTP naming.
            # This will be faster, assuming that most headers are looked
            # up only once, and not all headers will be requested.
            return self._headers[name.upper().replace('-', '_')]
        except KeyError:
            return default

    def try_get_param(self, name, default=None):
        """Return a URI parameter value as a string

        name -- Parameter name as specified in the route template. Note that
                names are case-sensitive (e.g., 'Id' != 'id').
        default -- Value to return in case the header is not found

        """

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in self._params:
            return self._params[name]

        return default
