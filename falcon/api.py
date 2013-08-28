"""Defines the API class.

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import inspect
import traceback

from falcon.request import Request
from falcon.response import Response
import falcon.responders
from falcon.status_codes import HTTP_416
from falcon import api_helpers as helpers

from falcon.http_error import HTTPError
from falcon import DEFAULT_MEDIA_TYPE


class API(object):
    """Provides routing and such for building a web service application

    This class is the main entry point into a Falcon-based app. It provides a
    callable WSGI interface and a simple routing engine based on URI templates.

    """

    __slots__ = ('_after', '_before', '_media_type', '_routes',
                 '_default_route')

    def __init__(self, media_type=DEFAULT_MEDIA_TYPE, before=None, after=None):
        """Initialize a new Falcon API instances

        Args:
            media_type: Default media type to use as the value for the
                Content-Type header on responses. (default 'application/json')
            before: A global action hook (or list of hooks) to call before
                each on_* responder, for all resources. Similar to the
                'falcon.before' decorator, but applies to the entire API. When
                more than one action function is given, they will be executed
                in natural order (starting with the first in the list).
            after: A global action hook (or list of hooks) to call after each
                on_* responder, for all resources. Similar to the 'after'
                decorator, but applies to the entire API.

        """

        self._routes = []
        self._default_route = None
        self._media_type = media_type

        self._before = helpers.prepare_global_hooks(before)
        self._after = helpers.prepare_global_hooks(after)

    def __call__(self, env, start_response):
        """WSGI "app" method

        Makes instances of API callable by any WSGI server. See also PEP 333.

        Args:
            env: A WSGI environment dictionary
            start_response: A WSGI helper method for setting status and headers
                on a response.

        """

        req = Request(env)
        resp = Response()

        responder, params, na_responder = self._get_responder(
            req.path, req.method)

        try:
            responder(req, resp, **params)

        except HTTPError as ex:
            resp.status = ex.status
            if ex.headers is not None:
                resp.set_headers(ex.headers)

            if req.client_accepts('application/json'):
                resp.body = ex.json()

        except TypeError as ex:
            # NOTE(kgriffs): Get the stack trace up here since we can just
            # use this convenience function which graps the last raised
            # exception context.
            stack_trace = traceback.format_exc()

            # See if the method doesn't support the given route's params, to
            # support assigning multiple routes to the same resource.
            try:
                argspec = responder.wrapped_argspec
            except AttributeError:
                argspec = inspect.getargspec(responder)

            # First three args should be (self, req, resp)
            if argspec.args[0] == 'self':
                offset = 3
            else:
                offset = 2

            args_needed = set(argspec.args[offset:])
            args_given = set(params.keys())

            # Reset the response
            resp = Response()

            # Does the responder require more or fewer args than given?
            if args_needed != args_given:
                req.log_error('A responder method could not be found with the '
                              'correct arguments.')
                na_responder(req, resp)
            else:
                # Error caused by something else
                req.log_error('A responder method (on_*) raised TypeError. %s'
                              % stack_trace)
                falcon.responders.internal_server_error(req, resp)

        #
        # Set status and headers
        #
        use_body = not helpers.should_ignore_body(resp.status, req.method)
        if use_body:
            helpers.set_content_length(resp)
            body = helpers.get_body(resp)
        else:
            # Default: return an empty body
            body = []

        # Set content type if needed
        use_content_type = (body or
                            req.method == 'HEAD' or
                            resp.status == HTTP_416)

        if use_content_type:
            media_type = self._media_type
        else:
            media_type = None

        headers = resp._wsgi_headers(media_type)

        # Return the response per the WSGI spec
        start_response(resp.status, headers)
        return body

    def add_route(self, uri_template, resource):
        """Associate a URI path with a resource

        A resource is an instance of a class that defines various on_*
        "responder" methods, one for each HTTP method the resource
        allows. For example, to support GET, simply define an "on_get"
        responder. If a client requests an unsupported method, Falcon
        will respond with "405 Method not allowed".

        Responders must always define at least two arguments to receive
        request and response objects, respectively. For example:

            def on_post(self, req, resp):
                pass

        In addition, if the route's uri template contains field
        expressions, any responders that desires to receive requests
        for that route must accept arguments named after the respective
        field names defined in the template. For example, given the
        following uri template:

            /das/{thing}

        A PUT request to "/das/code" would be routed to:

            def on_put(self, req, resp, thing):
                pass

        If, on the other hand, the responder had been defined thus:

            def on_put(self, req, resp):
                pass

        Falcon would respond to the client's request with "405 Method
        not allowed." This allows you to define multiple routes to the
        same resource, e.g., in order to support GET for "/widget/1234"
        and POST to "/widgets". In this last example, a POST to
        "/widget/5000" would result in a 405 response.

        Args:
            uri_template: Relative URI template. Currently only Level 1
                templates are supported. See also RFC 6570.
            resource: Object which represents an HTTP/REST "resource". Falcon
                will pass "GET" requests to on_get, "PUT" requests to on_put,
                etc. If any HTTP methods are not supported by your resource,
                simply don't define the corresponding request handlers, and
                Falcon will do the right thing.

        """

        uri_fields, path_template = helpers.compile_uri_template(uri_template)
        method_map, na_responder = helpers.create_http_method_map(
            resource, uri_fields, self._before, self._after)

        # Insert at the head of the list in case we get duplicate
        # adds (will cause the last one to win).
        self._routes.insert(0, (path_template, method_map, na_responder))

    def set_default_route(self, default_resource):
        """Route all the unrouted requests to a default resource

        Args:
            default_resource: Object which works like an HTTP/REST resource.
                Falcon will pass "GET" requests to on_get, "PUT" requests to
                on_put, etc. If you want to exclude some HTTP method from the
                default routing, just simply don't define the corresponding
                request handlers.

        """

        self._default_route = helpers.create_http_method_map(
            default_resource, set(), self._before, self._after)

#----------------------------------------------------------------------------
# Helpers
#----------------------------------------------------------------------------

    def _get_responder(self, path, method):
        """Searches routes for a matching responder

        Args:
            path: URI path to search (without query string)
            method: HTTP method (uppercase) requested

        Returns:
            A 3-member tuple, containing a responder callable, a dict
            containing parsed path fields (if any were specified in
            the matching route's URI template), and a reference to
            the "method not allowed" responder for the resource.

        """

        for route in self._routes:
            path_template, method_map, na_responder = route
            m = path_template.match(path)
            if m:
                params = m.groupdict()

                try:
                    responder = method_map[method]
                except KeyError:
                    responder = falcon.responders.bad_request

                break
        else:
            params = {}

            if self._default_route is not None:
                method_map, na_responder = self._default_route

                try:
                    responder = method_map[method]
                except KeyError:
                    responder = falcon.responders.bad_request

            else:
                responder = falcon.responders.path_not_found
                na_responder = falcon.responders.create_method_not_allowed([])

        return (responder, params, na_responder)
