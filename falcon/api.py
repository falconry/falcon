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

import inspect
import re
import six

from falcon import api_helpers as helpers
from falcon import DEFAULT_MEDIA_TYPE
from falcon.http_error import HTTPError
from falcon.http_status import HTTPStatus
from falcon.request import Request, RequestOptions
from falcon.response import Response
import falcon.responders
from falcon import routing
import falcon.status_codes as status


class API(object):
    """This class is the main entry point into a Falcon-based app.

    Each API instance provides a callable WSGI interface and a routing engine.

    Args:
        media_type (str, optional): Default media type to use as the value for
            the Content-Type header on responses (default 'application/json').
        middleware(object or list, optional): One or more objects
            (instantiated classes) that implement the following middleware
            component interface::

                class ExampleComponent(object):
                    def process_request(self, req, resp):
                        \"""Process the request before routing it.

                        Args:
                            req: Request object that will eventually be
                                routed to an on_* responder method.
                            resp: Response object that will be routed to
                                the on_* responder.
                        \"""

                    def process_resource(self, req, resp, resource, params):
                        \"""Process the request and resource *after* routing.

                        Note:
                            This method is only called when the request matches
                            a route to a resource.

                        Args:
                            req: Request object that will be passed to the
                                routed responder.
                            resp: Response object that will be passed to the
                                responder.
                            resource: Resource object to which the request was
                                routed. May be None if no route was found for
                                the request.
                            params: A dict-like object representing any
                                additional params derived from the route's URI
                                template fields, that will be passed to the
                                resource's responder method as keyword
                                arguments.
                        \"""

                    def process_response(self, req, resp, resource)
                        \"""Post-processing of the response (after routing).

                        Args:
                            req: Request object.
                            resp: Response object.
                            resource: Resource object to which the request was
                                routed. May be None if no route was found
                                for the request.
                        \"""

            See also :ref:`Middleware <middleware>`.

        request_type (Request, optional): ``Request``-like class to use instead
            of Falcon's default class. Among other things, this feature
            affords inheriting from ``falcon.request.Request`` in order
            to override the ``context_type`` class variable.
            (default ``falcon.request.Request``)

        response_type (Response, optional): ``Response``-like class to use
            instead of Falcon's default class. (default
            ``falcon.response.Response``)

        router (object, optional): An instance of a custom router
            to use in lieu of the default engine.
            See also: :ref:`Routing <routing>`.

    Attributes:
        req_options (RequestOptions): A set of behavioral options related to
            incoming requests.
    """

    # PERF(kgriffs): Reference via self since that is faster than
    # module global...
    _BODILESS_STATUS_CODES = set([
        status.HTTP_100,
        status.HTTP_101,
        status.HTTP_204,
        status.HTTP_304
    ])

    _STREAM_BLOCK_SIZE = 8 * 1024  # 8 KiB

    __slots__ = ('_request_type', '_response_type',
                 '_error_handlers', '_media_type', '_router', '_sinks',
                 '_serialize_error', 'req_options', '_middleware')

    def __init__(self, media_type=DEFAULT_MEDIA_TYPE,
                 request_type=Request, response_type=Response,
                 middleware=None, router=None):
        self._sinks = []
        self._media_type = media_type

        # set middleware
        self._middleware = helpers.prepare_middleware(middleware)

        self._router = router or routing.DefaultRouter()

        self._request_type = request_type
        self._response_type = response_type

        self._error_handlers = []
        self._serialize_error = helpers.default_serialize_error
        self.req_options = RequestOptions()

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

        req = self._request_type(env, options=self.req_options)
        resp = self._response_type()
        resource = None
        middleware_stack = []  # Keep track of executed components
        params = {}

        try:
            # NOTE(kgriffs): Using an inner try..except in order to
            # address the case when err_handler raises HTTPError.

            # NOTE(kgriffs): Coverage is giving false negatives,
            # so disabled on relevant lines. All paths are tested
            # afaict.
            try:
                # NOTE(ealogar): The execution of request middleware should be
                # before routing. This will allow request mw to modify path.
                self._call_req_mw(middleware_stack, req, resp)
                # NOTE(warsaw): Moved this to inside the try except because it
                # is possible when using object-based traversal for
                # _get_responder() to fail.  An example is a case where an
                # object does not have the requested next-hop child resource.
                # In that case, the object being asked to dispatch to its
                # child will raise an HTTP exception signalling the problem,
                # e.g. a 404.
                responder, params, resource = self._get_responder(req)

                # NOTE(kgriffs): If the request did not match any route,
                # a default responder is returned and the resource is
                # None.
                if resource is not None:
                    self._call_rsrc_mw(middleware_stack, req, resp, resource,
                                       params)

                responder(req, resp, **params)
                self._call_resp_mw(middleware_stack, req, resp, resource)

            except Exception as ex:
                for err_type, err_handler in self._error_handlers:
                    if isinstance(ex, err_type):
                        err_handler(ex, req, resp, params)
                        self._call_resp_mw(middleware_stack, req, resp,
                                           resource)

                        break

                else:
                    # PERF(kgriffs): This will propagate HTTPError to
                    # the handler below. It makes handling HTTPError
                    # less efficient, but that is OK since error cases
                    # don't need to be as fast as the happy path, and
                    # indeed, should perhaps be slower to create
                    # backpressure on clients that are issuing bad
                    # requests.

                    # NOTE(ealogar): This will executed remaining
                    # process_response when no error_handler is given
                    # and for whatever exception. If an HTTPError is raised
                    # remaining process_response will be executed later.
                    self._call_resp_mw(middleware_stack, req, resp, resource)
                    raise

        except HTTPStatus as ex:
            self._compose_status_response(req, resp, ex)
            self._call_resp_mw(middleware_stack, req, resp, resource)

        except HTTPError as ex:
            self._compose_error_response(req, resp, ex)
            self._call_resp_mw(middleware_stack, req, resp, resource)

        #
        # Set status and headers
        #
        if req.method == 'HEAD' or resp.status in self._BODILESS_STATUS_CODES:
            body = []
        else:
            body, length = self._get_body(resp, env.get('wsgi.file_wrapper'))
            if length is not None:
                resp._headers['content-length'] = str(length)

        # NOTE(kgriffs): Based on wsgiref.validate's interpretation of
        # RFC 2616, as commented in that module's source code. The
        # presence of the Content-Length header is not similarly
        # enforced.
        if resp.status in (status.HTTP_204, status.HTTP_304):
            media_type = None
        else:
            media_type = self._media_type

        headers = resp._wsgi_headers(media_type)

        # Return the response per the WSGI spec
        start_response(resp.status, headers)
        return body

    def add_route(self, uri_template, resource, *args, **kwargs):
        """Associates a templatized URI path with a resource.

        A resource is an instance of a class that defines various
        "responder" methods, one for each HTTP method the resource
        allows. Responder names start with `on_` and are named according to
        which HTTP method they handle, as in `on_get`, `on_post`, `on_put`,
        etc.

        If your resource does not support a particular
        HTTP method, simply omit the corresponding responder and
        Falcon will reply with "405 Method not allowed" if that
        method is ever requested.

        Responders must always define at least two arguments to receive
        request and response objects, respectively. For example::

            def on_post(self, req, resp):
                pass

        In addition, if the route's template contains field
        expressions, any responder that desires to receive requests
        for that route must accept arguments named after the respective
        field names defined in the template. A field expression consists
        of a bracketed field name.

        For example, given the following template::

            /user/{name}

        A PUT request to "/user/kgriffs" would be routed to::

            def on_put(self, req, resp, name):
                pass

        Individual path segments may contain one or more field expressions.
        For example::

            /repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}

        Args:
            uri_template (str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered (see also `add_sink`).
            resource (instance): Object which represents a REST
                resource. Falcon will pass "GET" requests to on_get,
                "PUT" requests to on_put, etc. If any HTTP methods are not
                supported by your resource, simply don't define the
                corresponding request handlers, and Falcon will do the right
                thing.

        Note:
            Any additional args and kwargs not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router does not expect any additional arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes.

        """

        # NOTE(richardolsson): Doing the validation here means it doesn't have
        # to be duplicated in every future router implementation.
        if not isinstance(uri_template, six.string_types):
            raise TypeError('uri_template is not a string')

        if not uri_template.startswith('/'):
            raise ValueError("uri_template must start with '/'")

        if '//' in uri_template:
            raise ValueError("uri_template may not contain '//'")

        method_map = routing.create_http_method_map(resource)
        self._router.add_route(uri_template, method_map, resource, *args,
                               **kwargs)

    def add_sink(self, sink, prefix=r'/'):
        """Registers a sink method for the API.

        If no route matches a request, but the path in the requested URI
        matches a sink prefix, Falcon will pass control to the
        associated sink, regardless of the HTTP method requested.

        Using sinks, you can drain and dynamically handle a large number
        of routes, when creating static resources and responders would be
        impractical. For example, you might use a sink to create a smart
        proxy that forwards requests to one or more backend services.

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

                Warning:
                    If the prefix overlaps a registered route template,
                    the route will take precedence and mask the sink
                    (see also `add_route`).

        """

        if not hasattr(prefix, 'match'):
            # Assume it is a string
            prefix = re.compile(prefix)

        # NOTE(kgriffs): Insert at the head of the list such that
        # in the case of a duplicate prefix, the last one added
        # is preferred.
        self._sinks.insert(0, (prefix, sink))

    def add_error_handler(self, exception, handler=None):
        """Registers a handler for a given exception error type.

        Args:
            exception (type): Whenever an error occurs when handling a request
                that is an instance of this exception class, the associated
                handler will be called.
            handler (callable): A function or callable object taking the form
                ``func(ex, req, resp, params)``.

                If not specified explicitly, the handler will default to
                ``exception.handle``, where ``exception`` is the error
                type specified above, and ``handle`` is a static method
                (i.e., decorated with @staticmethod) that accepts
                the same params just described. For example::

                    class CustomException(CustomBaseException):

                        @staticmethod
                        def handle(ex, req, resp, params):
                            # TODO: Log the error
                            # Convert to an instance of falcon.HTTPError
                            raise falcon.HTTPError(falcon.HTTP_792)

                Note:
                    A handler can either raise an instance of ``HTTPError``
                    or modify `resp` manually in order to communicate
                    information about the issue to the client.

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

    def set_error_serializer(self, serializer):
        """Override the default serializer for instances of HTTPError.

        When a responder raises an instance of HTTPError, Falcon converts
        it to an HTTP response automatically. The default serializer
        supports JSON and XML, but may be overridden by this method to
        use a custom serializer in order to support other media types.

        The ``falcon.HTTPError`` class contains helper methods, such as
        `to_json()` and `to_dict()`, that can be used from within
        custom serializers. For example::

            def my_serializer(req, resp, exception):
                representation = None

                preferred = req.client_prefers(('application/x-yaml',
                                                'application/json'))

                if preferred is not None:
                    if preferred == 'application/json':
                        representation = exception.to_json()
                    else:
                        representation = yaml.dump(exception.to_dict(),
                                                   encoding=None)
                    resp.body = representation
                    resp.content_type = preferred

        Note:
            If a custom media type is used and the type includes a
            "+json" or "+xml" suffix, the default serializer will
            convert the error to JSON or XML, respectively. If this
            is not desirable, a custom error serializer may be used
            to override this behavior.

        Args:
            serializer (callable): A function taking the form
                ``func(req, resp, exception)``, where `req` is the request
                object that was passed to the responder method, `resp` is
                the response object, and `exception` is an instance of
                ``falcon.HTTPError``.

        """

        if len(inspect.getargspec(serializer).args) == 2:
            serializer = helpers.wrap_old_error_serializer(serializer)
        self._serialize_error = serializer

    # ------------------------------------------------------------------------
    # Helpers that require self
    # ------------------------------------------------------------------------

    def _get_responder(self, req):
        """Searches routes for a matching responder.

        Args:
            req: The request object.

        Returns:
            A 3-member tuple consisting of a responder callable,
            a ``dict`` containing parsed path fields (if any were specified in
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

        route = self._router.find(path)

        if route is not None:
            resource, method_map, params = route
        else:
            # NOTE(kgriffs): Older routers may indicate that no route
            # was found by returning (None, None, None). Therefore, we
            # normalize resource as the flag to indicate whether or not
            # a route was found, for the sake of backwards-compat.
            resource = None

        if resource is not None:
            try:
                responder = method_map[method]
            except KeyError:
                responder = falcon.responders.bad_request
        else:
            params = {}

            for pattern, sink in self._sinks:
                m = pattern.match(path)
                if m:
                    params = m.groupdict()
                    responder = sink

                    break
            else:
                responder = falcon.responders.path_not_found

        return (responder, params, resource)

    def _compose_status_response(self, req, resp, http_status):
        """Composes a response for the given HTTPStatus instance."""

        # PERF(kgriffs): The code to set the status and headers is identical
        # to that used in _compose_error_response(), but refactoring in the
        # name of DRY isn't worth the extra CPU cycles.
        resp.status = http_status.status

        if http_status.headers is not None:
            resp.set_headers(http_status.headers)

        # NOTE(kgriffs): If http_status.body is None, that's OK because
        # it's acceptable to set resp.body to None (to indicate no body).
        resp.body = http_status.body

    def _compose_error_response(self, req, resp, error):
        """Composes a response for the given HTTPError instance."""

        resp.status = error.status

        if error.headers is not None:
            resp.set_headers(error.headers)

        if error.has_representation:
            self._serialize_error(req, resp, error)

    def _call_req_mw(self, stack, req, resp):
        """Run process_request middleware methods."""

        for component in self._middleware:
            process_request, _, _ = component
            if process_request is not None:
                process_request(req, resp)

            # Put executed component on the stack
            stack.append(component)  # keep track from outside

    def _call_rsrc_mw(self, stack, req, resp, resource, params):
        """Run process_resource middleware methods."""

        for component in self._middleware:
            _, process_resource, _ = component
            if process_resource is not None:
                process_resource(req, resp, resource, params)

    def _call_resp_mw(self, stack, req, resp, resource):
        """Run process_response middleware."""

        while stack:
            _, _, process_response = stack.pop()
            if process_response is not None:
                process_response(req, resp, resource)

    # PERF(kgriffs): Moved from api_helpers since it is slightly faster
    # to call using self, and this function is called for most
    # requests.
    def _get_body(self, resp, wsgi_file_wrapper=None):
        """Converts resp content into an iterable as required by PEP 333

        Args:
            resp: Instance of falcon.Response
            wsgi_file_wrapper: Reference to wsgi.file_wrapper from the
                WSGI environ dict, if provided by the WSGI server. Used
                when resp.stream is a file-like object (default None).

        Returns:
            A two-member tuple of the form (iterable, content_length).
            The length is returned as ``None`` when unknown. The
            iterable is determined as follows:

                * If resp.body is not ``None``, returns [resp.body],
                  encoded as UTF-8 if it is a Unicode string.
                  Bytestrings are returned as-is.
                * If resp.data is not ``None``, returns [resp.data]
                * If resp.stream is not ``None``, returns resp.stream
                  iterable using wsgi.file_wrapper, if possible.
                * Otherwise, returns []

        """

        body = resp.body
        if body is not None:
            if not isinstance(body, bytes):
                body = body.encode('utf-8')

            return [body], len(body)

        data = resp.data
        if data is not None:
            return [data], len(data)

        stream = resp.stream
        if stream is not None:
            # NOTE(kgriffs): Heuristic to quickly check if stream is
            # file-like. Not perfect, but should be good enough until
            # proven otherwise.
            if hasattr(stream, 'read'):
                if wsgi_file_wrapper is not None:
                    # TODO(kgriffs): Make block size configurable at the
                    # global level, pending experimentation to see how
                    # useful that would be. See also the discussion on
                    # this GitHub PR: http://goo.gl/XGrtDz
                    iterable = wsgi_file_wrapper(stream,
                                                 self._STREAM_BLOCK_SIZE)
                else:
                    iterable = iter(
                        lambda: stream.read(self._STREAM_BLOCK_SIZE),
                        b''
                    )
            else:
                iterable = stream

            # NOTE(kgriffs): If resp.stream_len is None, content_length
            # will be as well; the caller of _get_body must handle this
            # case by not setting the Content-Length header.
            return iterable, resp.stream_len

        return [], 0
