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

"""falcon APIBuilder class."""

import functools

from falcon import API, api_helpers, routing
from falcon.constants import DEFAULT_MEDIA_TYPE, HTTP_METHODS, WEBDAV_METHODS
from falcon.request import Request
from falcon.response import Response


class APIBuilder:
    """
    This class wraps the API class of falcon to provide several benefits when
    building a new API:
        1) This class separates the concerns of building an API from using
            an API
        2) The mutation methods in this class return self, allowing for
            chained style building in addition to unchained. For example:
                app = APIBuilder() \
                    .add_get_route('/', foo_resource.get_foos) \
                    .build()
        3) This builder frees users from using the falcon expected function
            names in their resources.  We no longer need to name our
            functions using the 'on' prefixed to the method type like 'on_get',
            'on_head', etc.  Now we can name our functions 'get_user',
            'create_user', or 'update_password', if we so choose.
        4) This builder frees users from using hard-REST resource style
            mappings:
            4.1) This means we can just have a route execute a top level
                function, it does not HAVE to be a method on a class at all.
            4.2) Also, a resource can have multiple functions which are pointed
                to using the same HTTP method.  That is, it does not care about
                uris or method types, so a single resource could have multiple
                uri/resource pairs direct to it (as long as they are unique).
                For example we could have an update_password, update_username,
                update_email function all on the Users resource, all with the
                PUT HTTP method pointed at them, and all using slightly
                different uris (eg. /password, /username, /email).

    Calling the 'build' method of this object returns a WSGI compliant falcon
    API.
    """

    def __init__(self):
        self._media_type = DEFAULT_MEDIA_TYPE
        self._call_response_middleware_on_request_middleware_exception = True
        self._middlewares = []
        self._request_type = Request
        self._response_type = Response
        self._router = routing.DefaultRouter()
        self._error_serializer = api_helpers.default_serialize_error
        self._routes = {}
        self._error_handling_functions = []
        self._sinks = []
        self._static_routes = []

    def set_media_type(self, media_type):
        """Changes the media type from the default to the given value

        Args:
            media_type (str): the media type to use as the
                value for the Content-Type header on responses (default
                'application/json'). The ``falcon`` module provides a
                number of constants for common media types, such as
                ``falcon.MEDIA_MSGPACK``, ``falcon.MEDIA_YAML``,
                ``falcon.MEDIA_XML``, etc.

        Returns:
            The Builder object so that the call can be chained.
        """
        self._media_type = media_type
        return self

    def set_call_response_middleware_on_request_middleware_exception(self, should_call):
        """Changes the value of ``independent_middleware`` in the API

        Args:
            should_call (bool): Set to ``False`` if response
                middleware should not be executed independently of whether or
                not request middleware raises an exception (default
                ``True``). When this option is set to ``False``, a middleware
                component's ``process_response()`` method will NOT be called
                when that same component's ``process_request()`` (or that of
                a component higher up in the stack) raises an exception.

        Returns:
            The Builder object so that the call can be chained.
        """
        self._call_response_middleware_on_request_middleware_exception = should_call
        return self

    def set_request_type(self, request_type):
        """Changes the request type class from falcon's default

        Args:
            request_type (Request): ``Request``-like class to use instead
                of Falcon's default class. Among other things, this feature
                affords inheriting from ``falcon.request.Request`` in order
                to override the ``context_type`` class variable.
                (default ``falcon.request.Request``)

        Returns:
            The Builder object so that the call can be chained.
        """
        self._request_type = request_type
        return self

    def set_response_type(self, response_type):
        """Changes the response type class from falcon's default

        Args:
            response_type (Response): ``Response``-like class to use
                instead of Falcon's default class. (default
                ``falcon.response.Response``)

        Returns:
            The Builder object so that the call can be chained.
        """
        self._response_type = response_type
        return self

    def set_router(self, router):
        """Changes the router from falcon's default

        Args:
            router (object): An instance of a custom router
                to use in lieu of the default engine.
                (See also: :ref:`Custom Routers <routing_custom>`)

        Returns:
            The Builder object so that the call can be chained.
        """
        self._router = router
        return self

    def set_error_serializer(self, serializer):
        """Changes the error serializer from falcon's default

        Args:
            serializer (callable): A function which takes a
                request, response, and exception and serializes
                the error.

        Returns:
            The Builder object so that the call can be chained.
        """
        self._error_serializer = serializer
        return self

    def add_middleware(self, middleware):
        """Adds a single instance of middleware to the api

        Args:
            middleware(object): A single object (instantiated
                classes) that implement the middleware component
                interface outlined in api.py

        Raises:
            APIBuildException: if the given middleware is a list
                meant for the add_middlewares function instead.

        Returns:
            The Builder object so that the call can be chained.
        """
        if isinstance(middleware, list):
            raise APIBuildException(
                'Should only add a single middleware using `add_middleware`, '
                'call `add_middlewares` for a collection.')
        self._middlewares.append(middleware)
        return self

    def add_middlewares(self, middlewares):
        """Adds a list of of middlewares to the api

        Args:
            middlewares(list): A list of objects (instantiated
                classes) that implement the middleware component
                interface outlined in api.py

        Returns:
            The Builder object so that the call can be chained.
        """
        self._middlewares.extend(middlewares)
        return self

    def add_get_route(self, uri, route_func, **kwargs):
        """Adds a route to a function using the GET HTTP method.

        Args:
            uri(str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered.
            route_func(callable): A function which takes a request
                and response, and mutates the response into what
                should be returned to the caller.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route.
                This is largely a throwback to the original Falcon api
                and is no longer really needed thanks to passing in a
                named function.  If you use this, the underlying
                generated resource will have the suffix attached
                to the function name.

        Raises:
            APIBuildException: if the given route adds a uri which
                is already mapped for a GET method or if a kwarg
                overwrites another preset kwarg for the same URI.

        Returns:
            The Builder object so that the call can be chained.

        Note:
            Any additional keyword arguments not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router ignores any additional keyword arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes. Custom routers MUST
            accept such arguments using the variadic pattern (``**kwargs``), and
            ignore any keyword arguments that they don't support.
        """
        return self.add_method_route('GET', uri, route_func, **kwargs)

    def add_post_route(self, uri, route_func, **kwargs):
        """Adds a route to a function using the POST HTTP method.

        Args:
            uri(str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered.
            route_func(callable): A function which takes a request
                and response, and mutates the response into what
                should be returned to the caller.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route.
                This is largely a throwback to the original Falcon api
                and is no longer really needed thanks to passing in a
                named function.  If you use this, the underlying
                generated resource will have the suffix attached
                to the function name.

        Raises:
            APIBuildException: if the given route adds a uri which
                is already mapped for a POST method or if a kwarg
                overwrites another preset kwarg for the same URI.

        Returns:
            The Builder object so that the call can be chained.

        Note:
            Any additional keyword arguments not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router ignores any additional keyword arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes. Custom routers MUST
            accept such arguments using the variadic pattern (``**kwargs``), and
            ignore any keyword arguments that they don't support.
        """
        return self.add_method_route('POST', uri, route_func, **kwargs)

    def add_put_route(self, uri, route_func, **kwargs):
        """Adds a route to a function using the PUT HTTP method.

        Args:
            uri(str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered.
            route_func(callable): A function which takes a request
                and response, and mutates the response into what
                should be returned to the caller.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route.
                This is largely a throwback to the original Falcon api
                and is no longer really needed thanks to passing in a
                named function.  If you use this, the underlying
                generated resource will have the suffix attached
                to the function name.

        Raises:
            APIBuildException: if the given route adds a uri which
                is already mapped for a PUT method or if a kwarg
                overwrites another preset kwarg for the same URI.

        Returns:
            The Builder object so that the call can be chained.

        Note:
            Any additional keyword arguments not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router ignores any additional keyword arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes. Custom routers MUST
            accept such arguments using the variadic pattern (``**kwargs``), and
            ignore any keyword arguments that they don't support.
        """
        return self.add_method_route('PUT', uri, route_func, **kwargs)

    def add_delete_route(self, uri, route_func, **kwargs):
        """Adds a route to a function using the DELETE HTTP method.

        Args:
            uri(str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered.
            route_func(callable): A function which takes a request
                and response, and mutates the response into what
                should be returned to the caller.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route.
                This is largely a throwback to the original Falcon api
                and is no longer really needed thanks to passing in a
                named function.  If you use this, the underlying
                generated resource will have the suffix attached
                to the function name.

        Raises:
            APIBuildException: if the given route adds a uri which
                is already mapped for a DELETE method or if a kwarg
                overwrites another preset kwarg for the same URI.

        Returns:
            The Builder object so that the call can be chained.

        Note:
            Any additional keyword arguments not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router ignores any additional keyword arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes. Custom routers MUST
            accept such arguments using the variadic pattern (``**kwargs``), and
            ignore any keyword arguments that they don't support.
        """
        return self.add_method_route('DELETE', uri, route_func, **kwargs)

    def add_patch_route(self, uri, route_func, **kwargs):
        """Adds a route to a function using the PATCH HTTP method.

        Args:
            uri(str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered.
            route_func(callable): A function which takes a request
                and response, and mutates the response into what
                should be returned to the caller.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route.
                This is largely a throwback to the original Falcon api
                and is no longer really needed thanks to passing in a
                named function.  If you use this, the underlying
                generated resource will have the suffix attached
                to the function name.

        Raises:
            APIBuildException: if the given route adds a uri which
                is already mapped for a PATCH method or if a kwarg
                overwrites another preset kwarg for the same URI.

        Returns:
            The Builder object so that the call can be chained.

        Note:
            Any additional keyword arguments not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router ignores any additional keyword arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes. Custom routers MUST
            accept such arguments using the variadic pattern (``**kwargs``), and
            ignore any keyword arguments that they don't support.
        """
        return self.add_method_route('PATCH', uri, route_func, **kwargs)

    def add_head_route(self, uri, route_func, **kwargs):
        """Adds a route to a function using the HEAD HTTP method.

        Args:
            uri(str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered.
            route_func(callable): A function which takes a request
                and response, and mutates the response into what
                should be returned to the caller.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route.
                This is largely a throwback to the original Falcon api
                and is no longer really needed thanks to passing in a
                named function.  If you use this, the underlying
                generated resource will have the suffix attached
                to the function name.

        Raises:
            APIBuildException: if the given route adds a uri which
                is already mapped for a HEAD method or if a kwarg
                overwrites another preset kwarg for the same URI.

        Returns:
            The Builder object so that the call can be chained.

        Note:
            Any additional keyword arguments not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router ignores any additional keyword arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes. Custom routers MUST
            accept such arguments using the variadic pattern (``**kwargs``), and
            ignore any keyword arguments that they don't support.
        """
        return self.add_method_route('HEAD', uri, route_func, **kwargs)

    def add_options_route(self, uri, route_func, **kwargs):
        """Adds a route to a function using the OPTIONS HTTP method.

        Args:
            uri(str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered.
            route_func(callable): A function which takes a request
                and response, and mutates the response into what
                should be returned to the caller.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route.
                This is largely a throwback to the original Falcon api
                and is no longer really needed thanks to passing in a
                named function.  If you use this, the underlying
                generated resource will have the suffix attached
                to the function name.

        Raises:
            APIBuildException: if the given route adds a uri which
                is already mapped for a OPTIONS method or if a kwarg
                overwrites another preset kwarg for the same URI.

        Returns:
            The Builder object so that the call can be chained.

        Note:
            Any additional keyword arguments not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router ignores any additional keyword arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes. Custom routers MUST
            accept such arguments using the variadic pattern (``**kwargs``), and
            ignore any keyword arguments that they don't support.
        """
        return self.add_method_route('OPTIONS', uri, route_func, **kwargs)

    def add_method_route(self, http_method, uri, route_func, **kwargs):
        """Adds a route to a function using the given HTTP method.

        Args:
            http_method(str): One of falcons HTTP_METHODS by which to
                map this route to this function.
            uri(str): A templatized URI. Care must be
                taken to ensure the template does not mask any sink
                patterns, if any are registered.
            route_func(callable): A function which takes a request
                and response, and mutates the response into what
                should be returned to the caller.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route.
                This is largely a throwback to the original Falcon api
                and is no longer really needed thanks to passing in a
                named function.  If you use this, the underlying
                generated resource will have the suffix attached
                to the function name.

        Raises:
            APIBuildException: if the given route adds a uri which
                is already mapped for a HTTP method or if a kwarg
                overwrites another preset kwarg for the same URI.

        Returns:
            The Builder object so that the call can be chained.

        Note:
            Any additional keyword arguments not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router ignores any additional keyword arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes. Custom routers MUST
            accept such arguments using the variadic pattern (``**kwargs``), and
            ignore any keyword arguments that they don't support.
        """
        self._raise_on_invalid_http_method_types(http_method)

        if uri not in self._routes:
            self._routes[uri] = {}

        self._raise_on_adding_non_unique_uri_method_pair(uri, http_method)
        self._raise_on_overwrite_attempt_for_kwargs_on_uri(uri, **kwargs)

        self._routes[uri][http_method] = APIRouteFunction(route_func, **kwargs)
        return self

    def add_error_route(self, exception, on_exception_func=None):
        """Adds a method for handling a certain type of exception.

        Error handlers may be registered for any type, including
        :class:`~.HTTPError`. This feature provides a central location
        for logging and otherwise handling exceptions raised by
        responders, hooks, and middleware components.

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

        Args:
            exception (type): Whenever an error occurs when handling a request
                that is an instance of this exception class, the associated
                handler will be called.
            on_exception_func (callable): A function or callable object taking the form
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

        Returns:
            The Builder object so that the call can be chained.
        """
        self._error_handling_functions.append(
            ExceptionHandlingFunction(exception, on_exception_func))
        return self

    def add_sink(self, sink, prefix=r'/'):
        """Adds a sink method for the API.

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

        Returns:
            The Builder object so that the call can be chained.
        """
        self._sinks.append(APISink(sink, prefix))
        return self

    def add_static_route(self, prefix, directory, downloadable=False, fallback_filename=None):
        """Adds a route to a directory of static files.

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

        Returns:
            The Builder object so that the call can be chained.
        """
        self._static_routes.append(
            APIStaticRoute(prefix, directory, downloadable, fallback_filename))
        return self

    def build(self):
        """Builds the configured API object

        Returns:
            A WSGI compliant API: An instance of the API in api.py
        """

        api = API(
            router=self._router,
            media_type=self._media_type,
            request_type=self._request_type,
            response_type=self._response_type,
            middleware=self._middlewares,
            independent_middleware=self._call_response_middleware_on_request_middleware_exception
        )

        for uri, uri_method_routes in self._routes.items():

            merged_resource_kwargs = {}
            resource = self._compose_new_resource(uri_method_routes)
            for http_method, api_route_function in uri_method_routes.items():
                merged_resource_kwargs.update(api_route_function.kwargs)

            api.add_route(uri, resource, **merged_resource_kwargs)

        for error_func in self._error_handling_functions:
            api.add_error_handler(error_func.exception, error_func.func)

        for sink in self._sinks:
            api.add_sink(sink.sink, sink.prefix)

        for static_route in self._static_routes:
            api.add_static_route(
                static_route.prefix,
                static_route.directory,
                static_route.downloadable,
                static_route.fallback_filename)

        api.set_error_serializer(self._error_serializer)
        return api

    class BlankResource:
        """A empty class for monkey-patching a resource into"""
        pass

    @staticmethod
    def _compose_new_resource(resource_method_routes):
        """Monkey patch a resource for a given method route map"""
        resource = APIBuilder.BlankResource()

        for http_method in resource_method_routes:
            suffix = ''
            if 'suffix' in resource_method_routes[http_method].kwargs:
                suffix = '_' + resource_method_routes[http_method].kwargs['suffix']

            falcon_expected_method_name = 'on_' + http_method.lower() + suffix
            setattr(resource,
                    falcon_expected_method_name,
                    APIBuilder._generate_wrapped_partial_for_resource(
                        resource_method_routes[http_method]))
        return resource

    @staticmethod
    def _generate_wrapped_partial_for_resource(router_function):
        """Use functools to apply function information to new function"""
        return functools.update_wrapper(
            functools.partial(router_function.function),
            router_function.function)

    @staticmethod
    def _raise_on_invalid_http_method_types(http_method):
        """raise an exception if an unknown HTTP method is used."""
        if http_method not in HTTP_METHODS + WEBDAV_METHODS:
            raise APIBuildException(
                'HTTP METHOD must be one of {methods} of which {method}'
                'is not.'.format(methods=HTTP_METHODS + WEBDAV_METHODS, method=http_method))

    def _raise_on_overwrite_attempt_for_kwargs_on_uri(self, uri, **new_kwargs):
        """raise an exception if we try to overwrite a previously set kwarg for a uri"""
        for http_method, route_func in self._routes[uri].items():
            for existing_key, existing_value in route_func.kwargs.items():
                if existing_key in new_kwargs and existing_value != new_kwargs[existing_key]:
                    raise APIBuildException(
                        'A kwarg by name {key} already has a set value on the resource '
                        'mapped to {uri}. You can only set a single key value per '
                        'resource.'.format(key=existing_key, uri=uri))

    def _raise_on_adding_non_unique_uri_method_pair(self, uri, http_method):
        """raise an exception if we try to add a uri-method pair that has already been added"""
        if http_method in self._routes[uri]:
            raise APIBuildException(
                'A route already exists for {method} on uri: {uri}. Only set 1 route per uri and '
                'HTTP Method.'.format(method=http_method, uri=uri))


class APIBuildException(Exception):
    """Raised from builder if bad configuration is given."""
    pass


class APIRouteFunction:
    """A Named Data Class for the values of an API routes function."""
    def __init__(self, func, **kwargs):
        self._function = func
        self._kwargs = kwargs

    @property
    def function(self):
        return self._function

    @property
    def kwargs(self):
        return self._kwargs


class ExceptionHandlingFunction:
    """A Named Data Class for the values of an Exception Handling function."""
    def __init__(self, exception, func):
        self._function = func
        self._exception = exception

    @property
    def func(self):
        return self._function

    @property
    def exception(self):
        return self._exception


class APISink:
    """A Named Data class for an API sink."""
    def __init__(self, sink, prefix):
        self._sink = sink
        self._prefix = prefix

    @property
    def sink(self):
        return self._sink

    @property
    def prefix(self):
        return self._prefix


class APIStaticRoute:
    """A Named Data class for an API static route."""
    def __init__(self, prefix, directory, downloadable, fallback_filename):
        self._prefix = prefix
        self._directory = directory
        self._downloadable = downloadable
        self._fallback_filename = fallback_filename

    @property
    def prefix(self):
        return self._prefix

    @property
    def directory(self):
        return self._directory

    @property
    def downloadable(self):
        return self._downloadable

    @property
    def fallback_filename(self):
        return self._fallback_filename
