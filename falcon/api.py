# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

from falcon import api_helpers as helpers
from falcon.request import Request
from falcon.response import Response
import falcon.responders
from falcon.status_codes import HTTP_416

from falcon.http_error import HTTPError
from falcon import DEFAULT_MEDIA_TYPE


class API(object):
    """This class is the main entry point into a Falcon-based app.

    Each API instance provides a callable WSGI interface and a simple routing
    engine based on URI Templates (RFC 6570).

    Args:
        media_type (str, optional): Default media type to use as the value for
            the Content-Type header on responses. (default 'application/json')
        before (callable, optional): A global action hook (or list of hooks)
            to call before each on_* responder, for all resources. Similar to
            the ``falcon.before`` decorator, but applies to the entire API.
            When more than one hook is given, they will be executed
            in natural order (starting with the first in the list).
        after (callable, optional): A global action hook (or list of hooks)
            to call after each on_* responder, for all resources. Similar to
            the ``after`` decorator, but applies to the entire API.
        request_type (Request, optional): Request-alike class to use instead
            of Falcon's default class. Useful if you wish to extend
            ``falcon.request.Request`` with a custom ``context_type``.
            (default falcon.request.Request)
        response_type (Response, optional): Response-alike class to use
            instead of Falcon's default class. (default
            falcon.response.Response)

    """

    __slots__ = ('_after', '_before', '_request_type', '_response_type',
                 '_error_handlers', '_media_type',
                 '_routes', '_sinks')

    def __init__(self, media_type=DEFAULT_MEDIA_TYPE, before=None, after=None,
                 request_type=Request, response_type=Response):
        self._routes = []
        self._sinks = []
        self._media_type = media_type

        self._before = helpers.prepare_global_hooks(before)
        self._after = helpers.prepare_global_hooks(after)

        self._request_type = request_type
        self._response_type = response_type

        self._error_handlers = []

    def __call__(self, env, start_response):
        """WSGI `app` method.

        Makes instances of API callable from a WSGI server. May be used to
        host an API or called directly in order to simulate requests when
        testing the API.

        See also PEP 3333.

        Args:
            env (dict): A WSGI environment dictionary
            start_response (callable): A WSGI helper function for setting
                status and headers on a response.

        """

        req = self._request_type(env)
        resp = self._response_type()
        resource = None

        try:
            # NOTE(warsaw): Moved this to inside the try except because it's
            # possible when using object-based traversal for _get_responder()
            # to fail.  An example is a case where an object does not have the
            # requested next-hop child resource.  In that case, the object
            # being asked to dispatch to its child will raise an HTTP
            # exception signalling the problem, e.g. a 404.
            responder, params, resource = self._get_responder(req)
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
                        self._call_after_hooks(req, resp, resource)
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
            helpers.compose_error_response(req, resp, ex)
            self._call_after_hooks(req, resp, resource)

        #
        # Set status and headers
        #
        use_body = not helpers.should_ignore_body(resp.status, req.method)
        if use_body:
            helpers.set_content_length(resp)
            body = helpers.get_body(resp, env.get('wsgi.file_wrapper'))
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
        """Associates a URI path with a resource.

        A resource is an instance of a class that defines various on_*
        "responder" methods, one for each HTTP method the resource
        allows. For example, to support GET, simply define an `on_get`
        responder. If a client requests an unsupported method, Falcon
        will respond with "405 Method not allowed".

        Responders must always define at least two arguments to receive
        request and response objects, respectively. For example::

            def on_post(self, req, resp):
                pass

        In addition, if the route's uri template contains field
        expressions, any responder that desires to receive requests
        for that route must accept arguments named after the respective
        field names defined in the template. For example, given the
        following uri template::

            /das/{thing}

        A PUT request to "/das/code" would be routed to::

            def on_put(self, req, resp, thing):
                pass

        Args:
            uri_template (str): Relative URI template. Currently only Level 1
                templates are supported. See also RFC 6570. Care must be
                taken to ensure the template does not mask any sink
                patterns (see also ``add_sink``).
            resource (instance): Object which represents an HTTP/REST
                "resource". Falcon will pass "GET" requests to on_get,
                "PUT" requests to on_put, etc. If any HTTP methods are not
                supported by your resource, simply don't define the
                corresponding request handlers, and Falcon will do the right
                thing.

        """

        uri_fields, path_template = helpers.compile_uri_template(uri_template)
        method_map = helpers.create_http_method_map(
            resource, uri_fields, self._before, self._after)

        # Insert at the head of the list in case we get duplicate
        # adds (will cause the last one to win).
        self._routes.insert(0, (path_template, method_map, resource))

    def add_sink(self, sink, prefix=r'/'):
        """Adds a "sink" responder to the API.

        If no route matches a request, but the path in the requested URI
        matches the specified prefix, Falcon will pass control to the
        given sink, regardless of the HTTP method requested.

        Args:
            sink (callable): A callable taking the form ``func(req, resp)``.

            prefix (str): A regex string, typically starting with '/', which
                will trigger the sink if it matches the path portion of the
                request's URI. Both strings and precompiled regex objects
                may be specified. Characters are matched starting at the
                beginning of the URI path.

                Note:
                    Named groups are converted to kwargs and passed to
                    the sink as such.

                Note:
                    If the route collides with a route's URI template, the
                    route will mask the sink (see also ``add_route``).

        """

        if not hasattr(prefix, 'match'):
            # Assume it is a string
            prefix = re.compile(prefix)

        # NOTE(kgriffs): Insert at the head of the list such that
        # in the case of a duplicate prefix, the last one added
        # is preferred.
        self._sinks.insert(0, (prefix, sink))

    def add_error_handler(self, exception, handler=None):
        """Adds a handler for a given exception type.

        Args:
            exception (type): Whenever an error occurs when handling a request
                that is an instance of this exception class, the given
                handler callable will be used to handle the exception.
            handler (callable): A callable taking the form
                ``func(ex, req, resp, params)``, called
                when there is a matching exception raised when handling a
                request.

                Note:
                    If not specified, the handler will default to
                    ``exception.handle``, where ``exception`` is the error
                    type specified above, and ``handle`` is a static method
                    (i.e., decorated with @staticmethod) that accepts
                    the same params just described.

                Note:
                    A handler can either raise an instance of HTTPError
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
        # adds (will cause the most recently added one to win).
        self._error_handlers.insert(0, (exception, handler))

    # ------------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------------

    def _get_responder(self, req):
        """Searches routes for a matching responder.

        Args:
            req: The request object.

        Returns:
            A 3-member tuple consisting of a responder callable,
            a dict containing parsed path fields (if any were specified in
            the matching route's URI template), and a reference to the
            responder's resource instance.

        Note:
            If a responder was matched to the given URI, but the HTTP
            method was not found in the method_map for the responder,
            the responder callable element of the returned tuple will be
            `falcon.responder.bad_request`.

            Likewise, if no responder was matched for the given URI, then
            the responder callable element of the returned tuple will be
            `falcon.responder.path_not_found`
        """

        path = req.path
        method = req.method
        for path_template, method_map, resource in self._routes:
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
            resource = None

            for pattern, sink in self._sinks:
                m = pattern.match(path)
                if m:
                    params = m.groupdict()
                    responder = sink

                    break
            else:
                responder = falcon.responders.path_not_found

        return (responder, params, resource)

    def _call_after_hooks(self, req, resp, resource):
        """Executes each of the global "after" hooks, in turn."""

        if not self._after:
            return

        for hook in self._after:
            try:
                hook(req, resp, resource)
            except TypeError:
                # NOTE(kgriffs): Catching the TypeError is a heuristic to
                # detect old hooks that do not accept the "resource" param
                hook(req, resp)
