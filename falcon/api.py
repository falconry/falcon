from falcon.default_request_handlers import *
from falcon.status_codes import *

# TODO: __slots__
# TODO: log exceptions, trace execution, etc.

class Api:
    """WSGI application implementing a Falcon web API"""

    def __init__(self):
        self.routes = {}

    def __call__(self, environ, start_response):
        # PERF: Use literal constructor for dicts
        # PERF: Don't use multi-assignment
        ctx = {}
        req = {}
        resp = {}

        # TODO: What other things does req need?
        req['path'] = path = environ['PATH_INFO']


        # TODO
        # ctx.update(global_ctx_for_route)

        # PERF: Use try...except blocks when the key usually exists
        try:
            # TODO: Figure out a way to use codegen to make a state machine,
            #       may have to in order to support URI templates.
            handler = self.routes[path]
        except KeyError:
            handler = path_not_found_handler

        try:
            handler(ctx, req, resp)
        except:
            # TODO
            pass

        try:
            start_response(resp['status'], [('Content-Type', 'text/plain')])
        except:
            # TODO
            pass

        # PERF: Can't predict ratio of empty body to nonempty, so use
        #       "in" which is a good all-around performer.
        return [resp['body']] if 'body' in resp else []

    def add_route(self, uri_template, handler):
        self.routes[uri_template] = handler
        pass

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------


