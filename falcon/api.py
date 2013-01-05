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
        use_body = not self._should_ignore_body(resp.status)
        if use_body:
            self._set_content_length(env, req, resp)

        start_response(resp.status, resp._wsgi_headers())

        # Return an iterable for the body, per the WSGI spec
        if use_body:
            return [resp.body] if resp.body is not None else []

        # Ignore body based on status code
        return []

    def add_route(self, uri_template, handler):
        self.routes[uri_template] = handler
        pass

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _should_ignore_body(self, status):
        return (status.startswith('204') or
                status.startswith('1') or
                status.startswith('304'))

    def _set_content_length(self, env, req, resp):

        # Set Content-Length when given a fully-buffered body or stream length
        if resp.body is not None:
            resp.set_header('Content-Length', str(len(resp.body)))
        elif resp.stream_len is not None:
            resp.set_header('Content-Length', resp.stream_len)
        else:
            resp.set_header('Content-Length', 0)
