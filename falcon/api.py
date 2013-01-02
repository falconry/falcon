from falcon.request import Request
from falcon.response import Response

from falcon.default_request_handlers import *
from falcon.status_codes import *

# TODO: __slots__
# TODO: log exceptions, trace execution, etc.

class Api:
    """Provides routing and such for building a web service application"""

    def __init__(self):
        self.routes = {}

    def __call__(self, environ, start_response):
        """WSGI protocol handler"""

        # PERF: Use literal constructor for dicts
        ctx = {}

        # TODO
        # ctx.update(global_ctx_for_route)

        path = environ['PATH_INFO']
        req = Request(path)

        resp = Response()

        # PERF: Use try...except blocks when the key usually exists
        try:
            # TODO: Figure out a way to use codegen to make a state machine,
            #       may have to in order to support URI templates.
            handler = self.routes[path]
        except KeyError:
            handler = path_not_found_handler

        try:
            handler(ctx, req, resp)
        except Exception as ex:
            # TODO
            pass

        resp.set_header('Content-Type', 'text/plain')

        # Consider refactoring into functions, but be careful since that can 
        # affect performance...

        body = resp.body
        content_length = 0
        try:
            if body is not None:
                content_length = len(body)
        except Exception as ex:
            #TODO
            pass

        resp.set_header('Content-Length', content_length)
        headers = resp._wsgi_headers()

        try:
            start_response(resp.status, headers)
        except Exception as ex:
            # TODO
            pass

        # PERF: Can't predict ratio of empty body to nonempty, so use
        #       "in" which is a good all-around performer.
        return [body] if body is not None else []

    def add_route(self, uri_template, handler):
        self.routes[uri_template] = handler
        pass

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------


