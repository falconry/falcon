class Response:
    __slots__ = ('status', '_headers', 'body', 'stream')

    def __init__(self):
        self.status = None
        self._headers = {}
        self.body = None
        self.stream = None

    def set_header(self, name, value):
        self._headers[name] = str(value)

    #TODO: Add some helper functions and test them

    def _wsgi_headers(self):
        return [t for t in self._headers.items()]