from falcon.request import Request
from falcon.response import Response
from falcon import responders
from falcon.status_codes import *
from falcon.api_helpers import *

HTTP_METHODS = (
    'CONNECT',
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'POST',
    'PUT',
    'TRACE'
)


class Api:
    """Provides routing and such for building a web service application"""

    __slots__ = ('routes')

    def __init__(self):
        self.routes = []

    def __call__(self, env, start_response):
        """WSGI "app" method

        Makes instances of API callable by any WSGI server. See also PEP 333.

        """

        req = Request(env)
        resp = Response()

        path = req.path
        for path_template, method_map in self.routes:
            m = path_template.match(path)
            if m:
                req._params.update(m.groupdict())

                try:
                    responder = method_map[req.method]
                except KeyError:
                    responder = responders.bad_request

                break
        else:
            responder = responders.path_not_found

        responder(req, resp)

        #
        # Set status and headers
        #
        use_body = not should_ignore_body(resp.status)
        if use_body:
            set_content_length(env, req, resp)

        start_response(resp.status, resp._wsgi_headers())

        # Return an iterable for the body, per the WSGI spec
        if use_body:
            return [resp.body] if resp.body is not None else []

        # Ignore body on 1xx, 204, and 304
        return []

    def add_route(self, uri_template, resource):
        """Associate a URI path with a resource

        uri_template -- Relative URI template. Currently only Level 1 templates
                        are supported. See also RFC 6570.
        resource     -- Object which represents an HTTP/REST "resource". Falcon
                        will pass "GET" requests to on_get, "PUT" requests to
                        on_put, etc. If any HTTP methods are not supported by
                        your resource, simply don't define the corresponding
                        request handlers, and Falcon will do the right thing.

        """

        if not uri_template:
            uri_template = '/'

        path_template = compile_uri_template(uri_template)
        method_map = create_http_method_map(resource)

        self.routes.append((path_template, method_map))
