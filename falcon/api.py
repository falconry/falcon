# -*- coding: utf-8 -*-

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

"""Falcon API class."""

from functools import wraps
import re

from falcon import api_helpers as helpers, DEFAULT_MEDIA_TYPE, routing
from falcon.http_error import HTTPError
from falcon.http_status import HTTPStatus
from falcon.request import Request, RequestOptions
import falcon.responders
from falcon.response import Response, ResponseOptions
import falcon.status_codes as status
from falcon.util import compat, misc


# PERF(vytas): on Python 2.7+, Python 3.5+ (including cythonized modules),
# reference via module global is faster than going via self
_BODILESS_STATUS_CODES = frozenset([
    status.HTTP_100,
    status.HTTP_101,
    status.HTTP_204,
    status.HTTP_304,
])

_TYPELESS_STATUS_CODES = frozenset([
    status.HTTP_204,
    status.HTTP_304,
])


class API(object):
    """This class is the main entry point into a Falcon-based app.

    Each API instance provides a callable WSGI interface and a routing
    engine.

    Keyword Arguments:
        media_type (str): Default media type to use as the
            value for the Content-Type header on responses (default
            'application/json'). The ``falcon`` module provides a
            number of constants for common media types, such as
            ``falcon.MEDIA_MSGPACK``, ``falcon.MEDIA_YAML``,
            ``falcon.MEDIA_XML``, etc.
        middleware(object or list): Either a single object or a list
            of objects (instantiated classes) that implement the
            following middleware component interface::

                class ExampleComponent(object):
                    def process_request(self, req, resp):
                        \"\"\"Process the request before routing it.

                        Note:
                            Because Falcon routes each request based on
                            req.path, a request can be effectively re-routed
                            by setting that attribute to a new value from
                            within process_request().

                        Args:
                            req: Request object that will eventually be
                                routed to an on_* responder method.
                            resp: Response object that will be routed to
                                the on_* responder.
                        \"\"\"

                    def process_resource(self, req, resp, resource, params):
                        \"\"\"Process the request and resource *after* routing.

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
                        \"\"\"

                    def process_response(self, req, resp, resource, req_succeeded)
                        \"\"\"Post-processing of the response (after routing).

                        Args:
                            req: Request object.
                            resp: Response object.
                            resource: Resource object to which the request was
                                routed. May be None if no route was found
                                for the request.
                            req_succeeded: True if no exceptions were raised
                                while the framework processed and routed the
                                request; otherwise False.
                        \"\"\"

            (See also: :ref:`Middleware <middleware>`)

        request_type (Request): ``Request``-like class to use instead
            of Falcon's default class. Among other things, this feature
            affords inheriting from ``falcon.request.Request`` in order
            to override the ``context_type`` class variable.
            (default ``falcon.request.Request``)

        response_type (Response): ``Response``-like class to use
            instead of Falcon's default class. (default
            ``falcon.response.Response``)

        router (object): An instance of a custom router
            to use in lieu of the default engine.
            (See also: :ref:`Custom Routers <routing_custom>`)

        independent_middleware (bool): Set to ``False`` if response
            middleware should not be executed independently of whether or
            not request middleware raises an exception (default
            ``True``). When this option is set to ``False``, a middleware
            component's ``process_response()`` method will NOT be called
            when that same component's ``process_request()`` (or that of
            a component higher up in the stack) raises an exception.

    Attributes:
        req_options: A set of behavioral options related to incoming
            requests. (See also: :py:class:`~.RequestOptions`)
        resp_options: A set of behavioral options related to outgoing
            responses. (See also: :py:class:`~.ResponseOptions`)
        router_options: Configuration options for the router. If a
            custom router is in use, and it does not expose any
            configurable options, referencing this attribute will raise
            an instance of ``AttributeError``.

            (See also: :ref:`CompiledRouterOptions <compiled_router_options>`)
    """

    _STREAM_BLOCK_SIZE = 8 * 1024  # 8 KiB

    __slots__ = ('_request_type', '_response_type',
                 '_error_handlers', '_media_type', '_router', '_sinks',
                 '_serialize_error', 'req_options', 'resp_options',
                 '_middleware', '_independent_middleware', '_router_search',
                 '_static_routes')

    def __init__(self, media_type=DEFAULT_MEDIA_TYPE,
                 request_type=Request, response_type=Response,
                 middleware=None, router=None,
                 independent_middleware=True):
        self._sinks = []
        self._media_type = media_type
        self._static_routes = []

        # set middleware
        self._middleware = helpers.prepare_middleware(
            middleware, independent_middleware=independent_middleware)
        self._independent_middleware = independent_middleware

        self._router = router or routing.DefaultRouter()
        self._router_search = self._router.find

        self._request_type = request_type
        self._response_type = response_type

        self._error_handlers = []
        self._serialize_error = helpers.default_serialize_error

        self.req_options = RequestOptions()
        self.resp_options = ResponseOptions()

        self.req_options.default_media_type = media_type
        self.resp_options.default_media_type = media_type

        # NOTE(kgriffs): Add default error handlers
        self.add_error_handler(falcon.HTTPError, self._http_error_handler)
        self.add_error_handler(falcon.HTTPStatus, self._http_status_handler)

    def __call__(self, env, start_response):  # noqa: C901
        """WSGI `app` method.

        Makes instances of API callable from a WSGI server. May be used to
        host an API or called directly in order to simulate requests when
        testing the API.

        (See also: PEP 3333)

        Args:
            env (dict): A WSGI environment dictionary
            start_response (callable): A WSGI helper function for setting
                status and headers on a response.

        """

        req = self._request_type(env, options=self.req_options)
        resp = self._response_type(options=self.resp_options)
        resource = None
        responder = None
        params = {}

        dependent_mw_resp_stack = []
        mw_req_stack, mw_rsrc_stack, mw_resp_stack = self._middleware

        req_succeeded = False

        try:
            try:
                # NOTE(ealogar): The execution of request middleware
                # should be before routing. This will allow request mw
                # to modify the path.
                # NOTE: if flag set to use independent middleware, execute
                # request middleware independently. Otherwise, only queue
                # response middleware after request middleware succeeds.
                if self._independent_middleware:
                    for process_request in mw_req_stack:
                        process_request(req, resp)
                        if resp.complete:
                            break
                else:
                    for process_request, process_response in mw_req_stack:
                        if process_request and not resp.complete:
                            process_request(req, resp)
                        if process_response:
                            dependent_mw_resp_stack.insert(0, process_response)

                if not resp.complete:
                    # NOTE(warsaw): Moved this to inside the try except
                    # because it is possible when using object-based
                    # traversal for _get_responder() to fail.  An example is
                    # a case where an object does not have the requested
                    # next-hop child resource. In that case, the object
                    # being asked to dispatch to its child will raise an
                    # HTTP exception signalling the problem, e.g. a 404.
                    responder, params, resource, req.uri_template = self._get_responder(req)
            except Exception as ex:
                if not self._handle_exception(req, resp, ex, params):
                    raise
            else:
                try:
                    # NOTE(kgriffs): If the request did not match any
                    # route, a default responder is returned and the
                    # resource is None. In that case, we skip the
                    # resource middleware methods. Resource will also be
                    # None when a middleware method already set
                    # resp.complete to True.
                    if resource:
                        # Call process_resource middleware methods.
                        for process_resource in mw_rsrc_stack:
                            process_resource(req, resp, resource, params)
                            if resp.complete:
                                break

                    if not resp.complete:
                        responder(req, resp, **params)

                    req_succeeded = True
                except Exception as ex:
                    if not self._handle_exception(req, resp, ex, params):
                        raise
        finally:
            # NOTE(kgriffs): It may not be useful to still execute
            # response middleware methods in the case of an unhandled
            # exception, but this is done for the sake of backwards
            # compatibility, since it was incidentally the behavior in
            # the 1.0 release before this section of the code was
            # reworked.

            # Call process_response middleware methods.
            for process_response in mw_resp_stack or dependent_mw_resp_stack:
                try:
                    process_response(req, resp, resource, req_succeeded)
                except Exception as ex:
                    if not self._handle_exception(req, resp, ex, params):
                        raise

                    req_succeeded = False

        #
        # Set status and headers
        #

        # NOTE(kgriffs): While not specified in the spec that the status
        # must be of type str (not unicode on Py27), some WSGI servers
        # can complain when it is not.
        resp_status = str(resp.status) if compat.PY2 else resp.status
        media_type = self._media_type

        if req.method == 'HEAD' or resp_status in _BODILESS_STATUS_CODES:
            body = []

            # PERF(vytas): move check for the less common and much faster path
            # of resp_status being in {204, 304} here; NB: this builds on the
            # assumption _TYPELESS_STATUS_CODES <= _BODILESS_STATUS_CODES.

            # NOTE(kgriffs): Based on wsgiref.validate's interpretation of
            # RFC 2616, as commented in that module's source code. The
            # presence of the Content-Length header is not similarly
            # enforced.
            if resp_status in _TYPELESS_STATUS_CODES:
                media_type = None

        else:
            body, length = self._get_body(resp, env.get('wsgi.file_wrapper'))

            # PERF(kgriffs): Böse mußt sein. Operate directly on resp._headers
            #   to reduce overhead since this is a hot/critical code path.
            # NOTE(kgriffs): We always set content-length to match the
            #   body bytes length, even if content-length is already set. The
            #   reason being that web servers and LBs behave unpredictably
            #   when the header doesn't match the body (sometimes choosing to
            #   drop the HTTP connection prematurely, for example).
            if length is not None:
                resp._headers['content-length'] = str(length)

        headers = resp._wsgi_headers(media_type)

        # Return the response per the WSGI spec.
        start_response(resp_status, headers)
        return body

    @property
    def router_options(self):
        return self._router.options

    def add_route(self, uri_template, resource, **kwargs):
        """Associate a templatized URI path with a resource.

        Falcon routes incoming requests to resources based on a set of
        URI templates. If the path requested by the client matches the
        template for a given route, the request is then passed on to the
        associated resource for processing.

        If no route matches the request, control then passes to a
        default responder that simply raises an instance of
        :class:`~.HTTPNotFound`.

        This method delegates to the configured router's ``add_route()``
        method. To override the default behavior, pass a custom router
        object to the :class:`~.API` initializer.

        (See also: :ref:`Routing <routing>`)

        Args:
            uri_template (str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered.

                (See also: :meth:`~.add_sink`)

            resource (instance): Object which represents a REST
                resource. Falcon will pass GET requests to ``on_get()``,
                PUT requests to ``on_put()``, etc. If any HTTP methods are not
                supported by your resource, simply don't define the
                corresponding request handlers, and Falcon will do the right
                thing.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route. If
                a suffix is provided, Falcon will map GET requests to
                ``on_get_{suffix}()``, POST requests to ``on_post_{suffix}()``,
                etc. In this way, multiple closely-related routes can be
                mapped to the same resource. For example, a single resource
                class can use suffixed responders to distinguish requests
                for a single item vs. a collection of those same items.
                Another class might use a suffixed responder to handle
                a shortlink route in addition to the regular route for the
                resource.

        Note:
            Any additional keyword arguments not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router ignores any additional keyword arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes. Custom routers MUST
            accept such arguments using the variadic pattern (``**kwargs``), and
            ignore any keyword arguments that they don't support.
        """

        # NOTE(richardolsson): Doing the validation here means it doesn't have
        # to be duplicated in every future router implementation.
        if not isinstance(uri_template, compat.string_types):
            raise TypeError('uri_template is not a string')

        if not uri_template.startswith('/'):
            raise ValueError("uri_template must start with '/'")

        if '//' in uri_template:
            raise ValueError("uri_template may not contain '//'")

        self._router.add_route(uri_template, resource, **kwargs)

    def add_static_route(self, prefix, directory, downloadable=False, fallback_filename=None):
        """Add a route to a directory of static files.

        Static routes provide a way to serve files directly. This
        feature provides an alternative to serving files at the web server
        level when you don't have that option, when authorization is
        required, or for testing purposes.

        Warning:
            Serving files directly from the web server,
            rather than through the Python app, will always be more efficient,
            and therefore should be preferred in production deployments.
            For security reasons, the directory and the fallback_filename (if provided)
            should be read only for the account running the application.

        Static routes are matched in LIFO order. Therefore, if the same
        prefix is used for two routes, the second one will override the
        first. This also means that more specific routes should be added
        *after* less specific ones. For example, the following sequence
        would result in ``'/foo/bar/thing.js'`` being mapped to the
        ``'/foo/bar'`` route, and ``'/foo/xyz/thing.js'`` being mapped to the
        ``'/foo'`` route::

            api.add_static_route('/foo', foo_path)
            api.add_static_route('/foo/bar', foobar_path)

        Args:
            prefix (str): The path prefix to match for this route. If the
                path in the requested URI starts with this string, the remainder
                of the path will be appended to the source directory to
                determine the file to serve. This is done in a secure manner
                to prevent an attacker from requesting a file outside the
                specified directory.

                Note that static routes are matched in LIFO order, and are only
                attempted after checking dynamic routes and sinks.

            directory (str): The source directory from which to serve files.
            downloadable (bool): Set to ``True`` to include a
                Content-Disposition header in the response. The "filename"
                directive is simply set to the name of the requested file.
            fallback_filename (str): Fallback filename used when the requested file
                is not found. Can be a relative path inside the prefix folder or any valid
                absolute path.

        """

        self._static_routes.insert(
            0,
            routing.StaticRoute(prefix, directory, downloadable=downloadable,
                                fallback_filename=fallback_filename)
        )

    def add_sink(self, sink, prefix=r'/'):
        """Register a sink method for the API.

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
                    the route will take precedence and mask the sink.

                    (See also: :meth:`~.add_route`)

        """

        if not hasattr(prefix, 'match'):
            # Assume it is a string
            prefix = re.compile(prefix)

        # NOTE(kgriffs): Insert at the head of the list such that
        # in the case of a duplicate prefix, the last one added
        # is preferred.
        self._sinks.insert(0, (prefix, sink))

    def add_error_handler(self, exception, handler=None):
        """Register a handler for one or more exception types.

        Error handlers may be registered for any exception type, including
        :class:`~.HTTPError` or :class:`~.HTTPStatus`. This feature
        provides a central location for logging and otherwise handling
        exceptions raised by responders, hooks, and middleware components.

        A handler can raise an instance of :class:`~.HTTPError` or
        :class:`~.HTTPStatus` to communicate information about the issue to
        the client.  Alternatively, a handler may modify `resp`
        directly.

        Error handlers are matched in LIFO order. In other words, when
        searching for an error handler to match a raised exception, and
        more than one handler matches the exception type, the framework
        will choose the one that was most recently registered.
        Therefore, more general error handlers (e.g., for the
        standard ``Exception`` type) should be added first, to avoid
        masking more specific handlers for subclassed types.

        .. Note::

            By default, the framework installs two handlers, one for
            :class:`~.HTTPError` and one for :class:`~.HTTPStatus`. These can
            be overridden by adding a custom error handler method for the
            exception type in question.

        Args:
            exception (type or iterable of types): When handling a request,
                whenever an error occurs that is an instance of the specified
                type(s), the associated handler will be called. Either a single
                type or an iterable of types may be specified.
            handler (callable): A function or callable object taking the form
                ``func(req, resp, ex, params)``.

                If not specified explicitly, the handler will default to
                ``exception.handle``, where ``exception`` is the error
                type specified above, and ``handle`` is a static method
                (i.e., decorated with @staticmethod) that accepts
                the same params just described. For example::

                    class CustomException(CustomBaseException):

                        @staticmethod
                        def handle(req, resp, ex, params):
                            # TODO: Log the error
                            # Convert to an instance of falcon.HTTPError
                            raise falcon.HTTPError(falcon.HTTP_792)

                If an iterable of exception types is specified instead of
                a single type, the handler must be explicitly specified.

        """
        def wrap_old_handler(old_handler):
            @wraps(old_handler)
            def handler(req, resp, ex, params):
                old_handler(ex, req, resp, params)
            return handler

        if handler is None:
            try:
                handler = exception.handle
            except AttributeError:
                raise AttributeError('handler must either be specified '
                                     'explicitly or defined as a static'
                                     'method named "handle" that is a '
                                     'member of the given exception class.')

        # TODO(vytas): Remove this shimming in a future Falcon version.
        arg_names = tuple(misc.get_argnames(handler))
        if (arg_names[0:1] in (('e',), ('err',), ('error',), ('ex',), ('exception',)) or
                arg_names[1:3] in (('req', 'resp'), ('request', 'response'))):
            handler = wrap_old_handler(handler)

        try:
            exception_tuple = tuple(exception)
        except TypeError:
            exception_tuple = (exception, )

        if all(issubclass(exc, BaseException) for exc in exception_tuple):
            # Insert at the head of the list in case we get duplicate
            # adds (will cause the most recently added one to win).
            if len(exception_tuple) == 1:
                # In this case, insert only the single exception type
                # (not a tuple), to avoid unnnecessary overhead in the
                # exception handling path.
                self._error_handlers.insert(0, (exception_tuple[0], handler))
            else:
                self._error_handlers.insert(0, (exception_tuple, handler))
        else:
            raise TypeError('"exception" must be an exception type.')

    def set_error_serializer(self, serializer):
        """Override the default serializer for instances of :class:`~.HTTPError`.

        When a responder raises an instance of :class:`~.HTTPError`,
        Falcon converts it to an HTTP response automatically. The
        default serializer supports JSON and XML, but may be overridden
        by this method to use a custom serializer in order to support
        other media types.

        Note:
            If a custom media type is used and the type includes a
            "+json" or "+xml" suffix, the default serializer will
            convert the error to JSON or XML, respectively.

        Note:
            The default serializer will not render any response body for
            :class:`~.HTTPError` instances where the `has_representation`
            property evaluates to ``False`` (such as in the case of types
            that subclass :class:`falcon.http_error.NoRepresentation`).
            However a custom serializer will be called regardless of the
            property value, and it may choose to override the
            representation logic.

        The :class:`~.HTTPError` class contains helper methods,
        such as `to_json()` and `to_dict()`, that can be used from
        within custom serializers. For example::

            def my_serializer(req, resp, exception):
                representation = None

                preferred = req.client_prefers(('application/x-yaml',
                                                'application/json'))

                if exception.has_representation and preferred is not None:
                    if preferred == 'application/json':
                        representation = exception.to_json()
                    else:
                        representation = yaml.dump(exception.to_dict(),
                                                   encoding=None)
                    resp.body = representation
                    resp.content_type = preferred

                resp.append_header('Vary', 'Accept')

        Args:
            serializer (callable): A function taking the form
                ``func(req, resp, exception)``, where `req` is the request
                object that was passed to the responder method, `resp` is
                the response object, and `exception` is an instance of
                ``falcon.HTTPError``.

        """

        self._serialize_error = serializer

    # ------------------------------------------------------------------------
    # Helpers that require self
    # ------------------------------------------------------------------------

    def _get_responder(self, req):
        """Search routes for a matching responder.

        Args:
            req: The request object.

        Returns:
            tuple: A 4-member tuple consisting of a responder callable,
            a ``dict`` containing parsed path fields (if any were specified in
            the matching route's URI template), a reference to the responder's
            resource instance, and the matching URI template.

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
        uri_template = None

        route = self._router_search(path, req=req)

        if route is not None:
            try:
                resource, method_map, params, uri_template = route
            except ValueError:
                # NOTE(kgriffs): Older routers may not return the
                # template. But for performance reasons they should at
                # least return None if they don't support it.
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

                for sr in self._static_routes:
                    if sr.match(path):
                        responder = sr
                        break
                else:
                    responder = falcon.responders.path_not_found

        return (responder, params, resource, uri_template)

    def _compose_status_response(self, req, resp, http_status):
        """Compose a response for the given HTTPStatus instance."""

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
        """Compose a response for the given HTTPError instance."""

        resp.status = error.status

        if error.headers is not None:
            resp.set_headers(error.headers)

        self._serialize_error(req, resp, error)

    def _http_status_handler(self, req, resp, status, params):
        self._compose_status_response(req, resp, status)

    def _http_error_handler(self, req, resp, error, params):
        self._compose_error_response(req, resp, error)

    def _handle_exception(self, req, resp, ex, params):
        """Handle an exception raised from mw or a responder.

        Args:
            ex: Exception to handle
            req: Current request object to pass to the handler
                registered for the given exception type
            resp: Current response object to pass to the handler
                registered for the given exception type
            params: Responder params to pass to the handler
                registered for the given exception type

        Returns:
            bool: ``True`` if a handler was found and called for the
            exception, ``False`` otherwise.
        """

        for err_type, err_handler in self._error_handlers:
            if isinstance(ex, err_type):
                try:
                    err_handler(req, resp, ex, params)
                except HTTPStatus as status:
                    self._compose_status_response(req, resp, status)
                except HTTPError as error:
                    self._compose_error_response(req, resp, error)

                return True

        # NOTE(kgriffs): No error handlers are defined for ex
        # and it is not one of (HTTPStatus, HTTPError), since it
        # would have matched one of the corresponding default
        # handlers.
        return False

    # PERF(kgriffs): Moved from api_helpers since it is slightly faster
    # to call using self, and this function is called for most
    # requests.
    def _get_body(self, resp, wsgi_file_wrapper=None):
        """Convert resp content into an iterable as required by PEP 333

        Args:
            resp: Instance of falcon.Response
            wsgi_file_wrapper: Reference to wsgi.file_wrapper from the
                WSGI environ dict, if provided by the WSGI server. Used
                when resp.stream is a file-like object (default None).

        Returns:
            tuple: A two-member tuple of the form (iterable, content_length).
            The length is returned as ``None`` when unknown. The
            iterable is determined as follows:

                * If resp.body is not ``None``, returns
                  ([resp.body], len(resp.body)),
                  encoded as UTF-8 if it is a Unicode string.
                  Bytestrings are returned as-is.
                * If resp.data is not ``None``, returns ([resp.data], len(resp.data))
                * If resp.stream is not ``None``, returns resp.stream
                  iterable using wsgi.file_wrapper, if necessary:
                  (closeable_iterator, None)
                * Otherwise, returns ([], 0)

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
                    iterable = helpers.CloseableStreamIterator(stream, self._STREAM_BLOCK_SIZE)
            else:
                iterable = stream

            return iterable, None

        return [], 0
