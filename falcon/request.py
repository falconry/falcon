class Request:
    __slots__ = ('path', 'headers', 'app', 'query_string', 'method')

    def __init__(self, env):
        self.method = env['REQUEST_METHOD']
        self.path = env['PATH_INFO'] or '/'
        self.app = env['SCRIPT_NAME']
        self.query_string = env['QUERY_STRING']

        # Extract HTTP headers
        self.headers = headers = {}
        for key in env:
            if key.startswith('HTTP_'):
                headers[key[5:]] = env[key]

        # Per the WSGI spec, Content-Type is not under HTTP_*
        if 'CONTENT_TYPE' in env:
            headers['CONTENT_TYPE'] = env['CONTENT_TYPE']

        # Per the WSGI spec, Content-Length is not under HTTP_*
        if 'CONTENT_LENGTH' in env:
            headers['CONTENT_LENGTH'] = env['CONTENT_LENGTH']

        # Fallback to SERVER_* vars if host header not specified
        if 'HOST' not in headers:
            host = env['SERVER_NAME']
            port = env['SERVER_PORT']

            if port != '80':
                host = ''.join([host, ':', port])

            headers['HOST'] = host

    def get_header(self, name, default=None):
        """Return a header value as a string

        name -- Header name, case-insensitive (e.g., 'Content-Type')
        default -- Value to return in case the header is not found

        """

        headers = self.headers

        # Use try..except to optimize for the header existing in most cases
        try:
            # Don't take the time to cache beforehand, using HTTP naming.
            # Will be faster, assuming that most headers are looked up only
            # once, and not all headers will be requested.
            return headers[name.upper().replace('-', '_')]
        except KeyError as e:
            return default

