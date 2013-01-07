class Request:
    __slots__ = ('app', '_headers', 'method',
                 '_params', 'path', 'query_string')

    def __init__(self, env):
        self.method = env['REQUEST_METHOD']
        self.path = env['PATH_INFO'] or '/'
        self.app = env['SCRIPT_NAME']
        self.query_string = env['QUERY_STRING']

        # Will be filled in by caller
        self._params = {}

        #

        # Extract HTTP headers
        self._headers = _headers = {}
        for key in env:
            if key.startswith('HTTP_'):
                _headers[key[5:]] = env[key]

        # Per the WSGI spec, Content-Type is not under HTTP_*
        if 'CONTENT_TYPE' in env:
            _headers['CONTENT_TYPE'] = env['CONTENT_TYPE']

        # Per the WSGI spec, Content-Length is not under HTTP_*
        if 'CONTENT_LENGTH' in env:
            _headers['CONTENT_LENGTH'] = env['CONTENT_LENGTH']

        # Fallback to SERVER_* vars if host header not specified
        if 'HOST' not in _headers:
            host = env['SERVER_NAME']
            port = env['SERVER_PORT']

            if port != '80':
                host = ''.join([host, ':', port])

            _headers['HOST'] = host

    def get_header(self, name, default=None):
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
        except KeyError as e:
            return default

    def get_param(self, name, default=None):
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


