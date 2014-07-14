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

import re

from falcon import api_helpers as helpers
from falcon.request import Request
from falcon.response import Response
import falcon.responders
from falcon.status_codes import HTTP_416
from falcon import util

from falcon.http_error import HTTPError
from falcon import DEFAULT_MEDIA_TYPE


class API(object):
    """Provides routing and such for building a web service application

    This class is the main entry point into a Falcon-based app. It provides a
    callable WSGI interface and a simple routing engine based on URI templates.

    """

    __slots__ = ('_after', '_before', '_error_handlers', '_media_type',
                 '_routes', '_default_route', '_sinks')

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
        self._sinks = []
        self._default_route = None
        self._media_type = media_type

        self._before = helpers.prepare_global_hooks(before)
        self._after = helpers.prepare_global_hooks(after)

        self._error_handlers = []

    def __call__(self, env, start_response):
        """WSGI "app" method

        Makes instances of API callable by any WSGI server. See also PEP 333.

        Args:
            env: A WSGI environment dictionary
            start_response: A WSGI helper method for setting status and
                headers on a response.

        """

        req = Request(env)
        resp = Response()

        responder, params = self._get_responder(
            req.path, req.method)

        try:
            # NOTE(kgriffs): Using an inner try..except in order to
            # address the case when err_handler raises HTTPError.
            #
            # NOTE(kgriffs): Coverage is giving false negatives,
            # so disabled on relevant lines. All paths are tested
            # afaict.
            try:
                responder(req, resp, **params)  # pragma: no cover
            except Exception as ex:
                for err_type, err_handler in self._error_handlers:
                    if isinstance(ex, err_type):
                        err_handler(ex, req, resp, params)
                        break  # pragma: no cover

                else:
                    # PERF(kgriffs): This will propagate HTTPError to
                    # the handler below. It makes handling HTTPError
                    # less efficient, but that is OK since error cases
                    # don't need to be as fast as the happy path, and
                    # indeed, should perhaps be slower to create
                    # backpressure on clients that are issuing bad
                    # requests.
                    raise

        except HTTPError as ex:
            resp.status = ex.status
            if ex.headers is not None:
                resp.set_headers(ex.headers)

            if req.client_accepts('application/json'):
                resp.body = ex.json()

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
        allows. For example, to support GET, simply define an `on_get`
        responder. If a client requests an unsupported method, Falcon
        will respond with "405 Method not allowed".

        Responders must always define at least two arguments to receive
        request and response objects, respectively. For example:

            def on_post(self, req, resp):
                pass

        In addition, if the route's uri template contains field
        expressions, any responder that desires to receive requests
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

        Args:
            uri_template: Relative URI template. Currently only Level 1
                templates are supported. See also RFC 6570. Care must be
                taken to ensure the template does not mask any sink
                patterns (see also add_sink).
            resource: Object which represents an HTTP/REST "resource". Falcon
                will pass "GET" requests to on_get, "PUT" requests to on_put,
                etc. If any HTTP methods are not supported by your resource,
                simply don't define the corresponding request handlers, and
                Falcon will do the right thing.

        """

        uri_fields, path_template = helpers.compile_uri_template(uri_template)
        method_map = helpers.create_http_method_map(
            resource, uri_fields, self._before, self._after)

        # Insert at the head of the list in case we get duplicate
        # adds (will cause the last one to win).
        self._routes.insert(0, (path_template, method_map))

    def add_sink(self, sink, prefix=r'/'):
        """Add a "sink" responder to the API.

        If no route matches a request, but the path in the requested URI
        matches the specified prefix, Falcon will pass control to the
        given sink, regardless of the HTTP method requested.

        Args:
            sink: A callable of the form:

                 func(req, resp)

            prefix: A regex string, typically starting with '/', which
                will trigger the sink if it matches the path portion of the
                request's URI. Both strings and precompiled regex objects
                may be specified. Characters are matched starting at the
                beginning of the URI path.

                Named groups are converted to kwargs and passed to
                the sink as such.

                If the route collides with a route's URI template, the
                route will mask the sink (see also add_route).

        """

        if not hasattr(prefix, 'match'):
            # Assume it is a string
            prefix = re.compile(prefix)

        # NOTE(kgriffs): Insert at the head of the list such that
        # in the case of a duplicate prefix, the last one added
        # is preferred.
        self._sinks.insert(0, (prefix, sink))

    # TODO(kgriffs): Remove this functionality in Falcon version 0.2.0
    @util.deprecated('Please migrate to add_sink(...) ASAP.')
    def set_default_route(self, default_resource):
        """DEPRECATED: Route all the unrouted requests to a default resource

        NOTE: If a default route is defined, all sinks are ignored.

        Args:
            default_resource: Object which works like an HTTP/REST resource.
                Falcon will pass "GET" requests to on_get, "PUT" requests to
                on_put, etc. If you want to exclude some HTTP method from the
                default routing, just simply don't define the corresponding
                request handlers.

        """

        self._default_route = helpers.create_http_method_map(
            default_resource, set(), self._before, self._after)

    def add_error_handler(self, exception, handler=None):
        """Adds a handler for a given exception type

        Args:
            exception: Whenever an exception occurs when handling a request
                that is an instance of this exception class, the given
                handler callable will be used to handle the exception.
            handler: Callable that gets called with (ex, req, resp, params)
                when there is a matching exception when handling a
                request. If not specified, the handler will default to
                exception.handle, in which case the method is expected to
                be static (i.e., decorated with @staticmethod) and take
                the same params described above.

                Note: A handler can either raise an instance of HTTPError
                or modify resp manually in order to communicate information
                about the issue to the client.

        """

        if handler is None:
            try:
                handler = exception.handle
            except AttributeError:
                raise AttributeError('handler must either be specified '
                                     'explicitly or defined as a static'
                                     'method named "handle" that is a '
                                     'member of the given exception class.')

        # Insert at the head of the list in case we get duplicate
        # adds (will cause the last one to win).
        self._error_handlers.insert(0, (exception, handler))

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

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
            path_template, method_map = route
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

            if self._default_route is None:

                for pattern, sink in self._sinks:
                    m = pattern.match(path)
                    if m:
                        params = m.groupdict()
                        responder = sink

                        break
                else:
                    responder = falcon.responders.path_not_found

            else:
                method_map = self._default_route

                try:
                    responder = method_map[method]
                except KeyError:
                    responder = falcon.responders.bad_request

        return (responder, params)
