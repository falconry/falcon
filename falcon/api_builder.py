
from falcon import api_helpers as helpers, API, DEFAULT_MEDIA_TYPE, routing
from falcon.request import Request
from falcon.response import Response

import sys
import inspect


class APIBuilder:

    def __init__(self):
        self._media_type = DEFAULT_MEDIA_TYPE
        self._call_response_middleware_on_request_middleware_exception = True
        self._middlewares = []
        self._request_type = Request
        self._response_type = Response
        self._router = routing.DefaultRouter()
        self._error_serializer = helpers.default_serialize_error
        self._routes = {}
        self._error_handling_functions = []
        self._sinks = []
        self._static_routes = []

    def set_media_type(self, media_type):
        self._media_type = media_type
        return self

    def set_call_response_middleware_on_request_middleware_exception(self, should_call):
        self._call_response_middleware_on_request_middleware_exception = should_call
        return self

    def set_request_type(self, request_type):
        self._request_type = request_type
        return self

    def set_response_type(self, response_type):
        self._response_type = response_type
        return self

    def set_router(self, router):
        self._router = router
        return self

    def set_error_serializer(self, serializer):
        self._error_serializer = serializer
        return self

    def add_middleware(self, middleware):
        if isinstance(middleware, list):
            raise APIBuildException(
                "Should only add a single middleware using `add_middleware`, "
                "call `add_middlewares` for a collection.")
        self._middlewares.append(middleware)
        return self

    def add_middlewares(self, middlewares):
        self._middlewares.extend(middlewares)
        return self

    def add_get_route(self, uri, route_func, **kwargs):
        return self._add_route("GET", uri, route_func, **kwargs)

    def add_post_route(self, uri, route_func, **kwargs):
        return self._add_route("POST", uri, route_func, **kwargs)

    def add_put_route(self, uri, route_func, **kwargs):
        return self._add_route("PUT", uri, route_func, **kwargs)

    def add_delete_route(self, uri, route_func, **kwargs):
        return self._add_route("DELETE", uri, route_func, **kwargs)

    def add_error_route(self, exception, on_exception_func):
        self._error_handling_functions.append(ExceptionHandlingFunction(exception, on_exception_func))
        return self

    def add_sink(self, sink, prefix=r'/'):
        self._sinks.append(APISink(sink, prefix))
        return self

    def add_static_route(self, prefix, directory, downloadable=False, fallback_filename=None):
        self._static_routes.append(APIStaticRoute(prefix, directory, downloadable, fallback_filename))
        return self

    def build(self):

        api = API(
            media_type=self._media_type,
            request_type=self._request_type,
            response_type=self._response_type,
            middleware=self._middlewares,
        )

        this = self

        class ResourceWrapper:
            pass

        merged_kwargs = {}
        for uri, uri_method_routes in self._routes.items():
            resource = ResourceWrapper()

            if "GET" in uri_method_routes:
                def on_get(self, request, response):
                    uri_method_routes["GET"].function()(request, response)
                resource.on_get = on_get.__get__(resource)
                merged_kwargs.update(uri_method_routes["GET"].kwargs)  # TODO: What about collisions?

            if "POST" in uri_method_routes:
                def on_post(self, request, response):
                    uri_method_routes["POST"].function()(request, response)
                resource.on_post = on_post.__get__(resource)
                merged_kwargs.update(uri_method_routes["POST"].kwargs)

            if "PUT" in uri_method_routes:
                def on_put(self, request, response):
                    uri_method_routes["PUT"].function()(request, response)
                resource.on_put = on_put.__get__(resource)
                merged_kwargs.update(uri_method_routes["PUT"].kwargs)

            if "DELETE" in uri_method_routes:
                def on_delete(self, request, response):
                    uri_method_routes["DELETE"].function()(request, response)
                resource.on_delete = on_delete.__get__(resource)
                merged_kwargs.update(uri_method_routes["DELETE"].kwargs)
            api.add_route(uri, resource, **merged_kwargs)

        for error_func in self._error_handling_functions:
            api.add_error_handler(error_func.exception, error_func.func)

        for sink in self._sinks:
            api.add_sink(sink.sink, sink.prefix)

        api.set_error_serializer(self._error_serializer)
        return api

    def _add_route(self, http_method, uri, route_func, **kwargs):
        if uri not in self._routes:
            self._routes[uri] = {}
        if http_method in self._routes[uri]:
            raise APIBuildException(
                "A route already exists for {method} on uri: {uri}. Only set 1 route per uri and HTTP Method."
                    .format(method=http_method, uri=uri))
        self._routes[uri]["GET"] = APIRouteFunction(route_func, **kwargs)
        return self


class APIRouteFunction:

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


class APIBuildException(Exception):
    pass
