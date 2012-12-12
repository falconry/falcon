from default_request_handlers import *
from status_codes import *

# TODO: __slots__
# TODO: log exceptions, trace execution, etc.

class Context:
    """Request context for passing around the request state"""
    def __init__(self, environ):
        self.req_path = environ['PATH_INFO']

class Api:
    """WSGI application implementing a Falcon web API"""

    def __init__(self):
        self.routes = {}

    def __call__(self, environ, start_response):
        ctx = Context(environ)

        try:
            handler = self.routes[ctx.req_path]
        except KeyError:
            handler = path_not_found_handler

        try:
            handler(ctx)
        except:
            pass

        start_response(ctx.resp_status, [('Content-Type', 'text/plain')])
        return [ctx.resp_body]

    def add_route(self, uri_template, handler):
        self.routes[uri_template] = handler
        pass

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------


