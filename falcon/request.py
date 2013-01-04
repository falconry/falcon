class Request:
    __slots__ = ('path', 'headers')

    def __init__(self, env):
        self.path = env['PATH_INFO']
        self.headers = headers = {}

        # Extract HTTP headers
        for key in env:
            if key.startswith('HTTP_'):
                headers[key[5:]] = env[key]

    def get_header(self, name, default=None):
        """Return a header value as a string

        name -- Header name, case-insensitive
        default -- Value to return in case the header is not found

        """

        headers = self.headers

        # Optimize for the header existing in most cases
        try:
            return headers[name.upper()]
        except KeyError as e:
            return default

