class Response:
    __slots__ = ('status', '_headers', 'body', 'stream', 'stream_len')

    def __init__(self):
        self.status = None

        self._headers = {}

        self.body = None
        self.stream = None
        self.stream_len = None

    def set_header(self, name, value):
        self._headers[name] = str(value)

    def set_headers(self, headers_by_name):
        self._headers.update(headers_by_name)

    def _wsgi_headers(self):
        return self._headers.items()
