
import functools

from falcon import API, api_helpers, routing
from falcon.constants import DEFAULT_MEDIA_TYPE, HTTP_METHODS, WEBDAV_METHODS
from falcon.request import Request
from falcon.response import Response


class APIBuildException(Exception):
    pass


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


# TODO: Write a test using a free function
# TODO: Write a test using a resource with named functions
# TODO: Write a test using a resource with multiple functions for same method but different uri
# TODO: Write a test for each BuilderException
# TODO:

class APIBuilder:
    """
    Improved for several reasons:
        1) Separates the concerns of building an API from using and API
        2) Mutation methods return self, allowing for chained style building in addition
            to unchained
        3) Allows for adding of uri routing to functions without having to subscribe a
            naming convention (of on_get, on_put, etc), which allows for more explicit
            function names like (get_user, create_user, update_password, etc).
        4) Allows for non hard-rest resource style mappings:
            4.1) can just have a route execute a top level function, it does not HAVE to
                be a method on a resource
            4.2) a resource can have multiple functions, it does not have to care about
                uris or method types, so a single resource could have multiple uri/resource
                pairs direct to it (as long as they are unique). For example we could have
                an update_password, update_username, update_email function all on the Users
                resource, all with PUT method pointed at them, and all using slightly
                different uris (eg. /password, /username, /email).
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
                'Should only add a single middleware using `add_middleware`, '
                'call `add_middlewares` for a collection.')
        self._middlewares.append(middleware)
        return self

    def add_middlewares(self, middlewares):
        self._middlewares.extend(middlewares)
        return self

    def add_get_route(self, uri, route_func, **kwargs):
        return self.add_method_route('GET', uri, route_func, **kwargs)

    def add_post_route(self, uri, route_func, **kwargs):
        return self.add_method_route('POST', uri, route_func, **kwargs)

    def add_put_route(self, uri, route_func, **kwargs):
        return self.add_method_route('PUT', uri, route_func, **kwargs)

    def add_delete_route(self, uri, route_func, **kwargs):
        return self.add_method_route('DELETE', uri, route_func, **kwargs)

    def add_patch_route(self, uri, route_func, **kwargs):
        return self.add_method_route('PATCH', uri, route_func, **kwargs)

    def add_head_route(self, uri, route_func, **kwargs):
        return self.add_method_route('HEAD', uri, route_func, **kwargs)

    def add_options_route(self, uri, route_func, **kwargs):
        return self.add_method_route('OPTIONS', uri, route_func, **kwargs)

    def add_method_route(self, http_method, uri, route_func, **kwargs):

        self._raise_on_invalid_http_method_types(http_method)

        if uri not in self._routes:
            self._routes[uri] = {}

        self._raise_on_adding_non_unique_uri_method_pair(uri, http_method)
        self._raise_on_overwrite_attempt_for_kwargs_on_uri(uri, **kwargs)

        self._routes[uri][http_method] = APIRouteFunction(route_func, **kwargs)
        return self

    def add_error_route(self, exception, on_exception_func):
        self._error_handling_functions.append(
            ExceptionHandlingFunction(exception, on_exception_func))
        return self

    def add_sink(self, sink, prefix=r'/'):
        self._sinks.append(APISink(sink, prefix))
        return self

    def add_static_route(self, prefix, directory, downloadable=False, fallback_filename=None):
        self._static_routes.append(
            APIStaticRoute(prefix, directory, downloadable, fallback_filename))
        return self

    def build(self):

        api = API(
            media_type=self._media_type,
            request_type=self._request_type,
            response_type=self._response_type,
            middleware=self._middlewares,
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

        api.set_error_serializer(self._error_serializer)
        return api

    @staticmethod
    def _compose_new_resource(resource_method_routes):
        class BlankResource:
            pass

        resource = BlankResource()

        for http_method in resource_method_routes:

            # TODO: Document this -> the suffix stuff makes a lot less sense with this builder
            # TODO:     because we can now used named functions.  We add it here to maintain
            # TODO:     exact equality between the two usages (API vs APIBuilder)
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
        return functools.update_wrapper(
            functools.partial(router_function.function),
            router_function.function)

    @staticmethod
    def _raise_on_invalid_http_method_types(http_method):
        if http_method not in HTTP_METHODS + WEBDAV_METHODS:
            raise APIBuildException(
                'HTTP METHOD must be one of {methods} of which {method}'
                'is not.'.format(methods=HTTP_METHODS + WEBDAV_METHODS, method=http_method))

    def _raise_on_overwrite_attempt_for_kwargs_on_uri(self, uri, **new_kwargs):
        for http_method, route_func in self._routes[uri].items():
            for existing_key, existing_value in route_func.kwargs.items():
                if existing_key in new_kwargs and existing_value != new_kwargs[existing_key]:
                    raise APIBuildException(
                        'A kwarg by name {key} already has a set value on the resource '
                        'mapped to {uri}. You can only set a single key value per '
                        'resource.'.format(key=existing_key, uri=uri))

    def _raise_on_adding_non_unique_uri_method_pair(self, uri, http_method):
        if http_method in self._routes[uri]:
            raise APIBuildException(
                'A route already exists for {method} on uri: {uri}. Only set 1 route per uri and '
                'HTTP Method.'.format(method=http_method, uri=uri))
