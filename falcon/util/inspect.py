"""Inspect utilities for falcon applications"""
import inspect
from functools import partial

from falcon import App
from falcon.routing import CompiledRouter


def inspect_routes(app: App):
    """Inspects the routes of an application

    Args:
        app (App): The application to inspect

    Raises:
        TypeError: [description]

    Returns:
        List[RouteInfo]: The list of routes of the specified application
    """
    router = app._router

    inspect_function = _supported_routes.get(type(router))
    if inspect_function is None:
        raise TypeError(
            "Unsupported router class {}. Use `register_router` "
            "to register a function that can inspect the router "
            "used by the provided application".format(type(router))
        )
    return inspect_function(router)


def register_router(router_class):
    """Register a function to inspect a particular router

    This decorator registers a new function for a custom router
    class, so that it can be inspected with the function
    :func:`.inspect_routes`.
    An inspection class takes the router instance used by the
    application and returns a list of ``RouteInfo``

    Args:
        router_class (Type): The router class to register. If
            already registered an error will be raised
    """

    def wraps(fn):
        if router_class in _supported_routes:
            raise ValueError(
                "Another function is already registered"
                " for the router {}".format(router_class)
            )
        _supported_routes[router_class] = fn
        return fn

    return wraps


_supported_routes = {}


@register_router(CompiledRouter)
def inspect_compiled_router(router):
    """Recursive call which also handles printing output.

    Args:
        router (CompiledRouter): The router to inspect

    Returns
        List[RouteInfo]: A list of RouteInfo
    """

    def _traverse(roots, parent):
        for root in roots:
            if root.method_map:
                route_info = RouteInfo(parent + "/" + root.raw_segment)
                for method, func in root.method_map.items():
                    if isinstance(func, partial):
                        real_func = func.func
                    else:
                        real_func = func

                    try:
                        source_file = inspect.getsourcefile(real_func)
                        source_lines = inspect.getsourcelines(real_func)
                        source_info = "{}:{}".format(source_file, source_lines[1])
                    except TypeError:
                        # NOTE(vytas): If Falcon is cythonized, all default
                        # responders coming from cythonized modules will
                        # appear as built-in functions, and raise a
                        # TypeError when trying to locate the source file.
                        source_info = "[unknown file]"

                    module = inspect.getmodule(real_func)
                    internal = module.__name__.startswith("falcon.")

                    method_info = MathodInfo(
                        method, source_info, real_func.__name__, internal
                    )
                    route_info.methods.append(method_info)
                routes.append(route_info)

            if root.children:
                _traverse(root.children, parent + "/" + root.raw_segment)

    routes = []
    _traverse(router._roots, "")
    return routes


class MathodInfo:
    """Utility class that contains the description of a responder method

    Args:
        method (str): The http method of this responder
        source_info (str): The source path of this function
        function_name (str): Name of the function
        internal (bool): If this responder was added by falcon
    """

    def __init__(self, method, source_info, function_name, internal):
        self.method = method
        self.source_info = source_info
        self.function_name = function_name
        self.internal = internal

    def __str__(self):
        return "{} {} {}".format(
            self.method.upper(), self.function_name, self.source_info
        )


class RouteInfo:
    """Utility class that contains the information of a route

    Args:
        path (str): The path of this route

    Attributes:
        methods (List[MathodInfo]): List of method defined in the route
    """

    def __init__(self, path):
        self.path = path
        self.methods = []

    def as_string(self, verbose=False):
        if verbose:
            methods = self.methods
        else:
            methods = [m for m in self.methods if not m.internal]

        text = "⇒ {}".format(self.path)
        if not methods:
            return text

        method_text = ["   ├── {}".format(m) for m in methods[:-1]]
        method_text += ["   └── {}".format(m) for m in methods[-1:]]

        return "{}:\n{}".format(text, "\n".join(method_text))

    def __repr__(self):
        return self.as_string()
