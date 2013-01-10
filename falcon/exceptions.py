from .http_error import HTTPError

class HTTPBadRequest(HTTPError):

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_400, titile, description, **kwargs)
