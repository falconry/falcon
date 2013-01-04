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

    def __call__(self, env, start_response):
        """WSGI protocol handler"""

        # PERF: Use literal constructor for dicts
        ctx = {}

        # TODO
        # ctx.update(global_ctx_for_route)

        req = Request(env)
        resp = Response()

        # PERF: Use try...except blocks when the key usually exists
        try:
            # TODO: Figure out a way to use codegen to make a state machine,
            #       may have to in order to support URI templates.
            handler = self.routes[req.path]
        except KeyError:
            handler = path_not_found_handler

        handler(ctx, req, resp)

        #
        # Set status and headers
        #
        self._set_auto_resp_headers(env, req, resp)
        start_response(resp.status, resp._wsgi_headers())

        # Return an iterable for the body, per the WSGI spec
        return [resp.body] if resp.body is not None else []

    def add_route(self, uri_template, handler):
        self.routes[uri_template] = handler
        pass

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _set_auto_resp_headers(self, env, req, resp):
        # Set Content-Length when given a fully-buffered body
        if resp.body is not None:
            resp.set_header('Content-Length', str(len(resp.body)))
        elif resp.stream is not None:
            # TODO: if resp.stream_len is not None, don't use chunked
            pass
        else:
            resp.set_header('Content-Length', 0)

