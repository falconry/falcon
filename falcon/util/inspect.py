"""Inspect utilities for falcon applications"""
import inspect
from functools import partial

from falcon import App
from falcon.routing import CompiledRouter


def inspect_app(app: App):
    """Inspects an application

    Args:
        app (App): The application to inspect

    Returns:
        AppInfo: The information regarding the application.
            Call the ``as_string`` to obtain a string representation of it
    """
    routes = inspect_routes(app)
    static = inspect_static_routes(app)
    sinks = inspect_sinks(app)
    error_handlers = inspect_error_handlers(app)
    return AppInfo(routes, static, sinks, error_handlers)


def inspect_routes(app: App):
    """Inspects the routes of an application

    Args:
        app (App): The application to inspect

    Returns:
        List[RouteInfo]: The list of routes info of the application
    """
    router = app._router

    inspect_function = _supported_routers.get(type(router))
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
        if router_class in _supported_routers:
            raise ValueError(
                "Another function is already registered"
                " for the router {}".format(router_class)
            )
        _supported_routers[router_class] = fn
        return fn

    return wraps


# router inspection registry
_supported_routers = {}


def inspect_static_routes(app: App):
    """Inspects the static routes of an application

    Args:
        app (App): The application to inspect

    Returns:
        List[StaticRouteInfo]: The list of static routes of the application
    """
    routes = []
    for sr in app._static_routes:
        info = StaticRouteInfo(sr._prefix, sr._directory, sr._fallback_filename)
        routes.append(info)
    return routes


def inspect_sinks(app: App):
    """Inspects the sinks of an application

    Args:
        app (App): The application to inspect

    Returns:
        List[SinkInfo]: The list of sinks of the application
    """
    sinks = []
    for prefix, sink in app._sinks:
        source_info, name = _get_source_info_and_name(sink)
        info = SinkInfo(prefix.pattern, name, source_info)
        sinks.append(info)
    return sinks


def inspect_error_handlers(app: App):
    """Inspects the error handlers of an application

    Args:
        app (App): The application to inspect

    Returns:
        List[ErrorHandlerInfo]: The list of error handlers of the application
    """
    errors = []
    for exc, fn in app._error_handlers.items():
        source_info, name = _get_source_info_and_name(fn)
        info = ErrorHandlerInfo(exc.__name__, name, source_info, _is_internal(fn))
        errors.append(info)
    return errors


def _get_source_info(obj, default="[unknown file]"):
    """Tries to get the definition file and line of obj. Returns default on error"""
    try:
        source_file = inspect.getsourcefile(obj)
        source_lines = inspect.getsourcelines(obj)
        source_info = "{}:{}".format(source_file, source_lines[1])
    except TypeError:
        # NOTE(vytas): If Falcon is cythonized, all default
        # responders coming from cythonized modules will
        # appear as built-in functions, and raise a
        # TypeError when trying to locate the source file.
        source_info = default
    return source_info


def _get_source_info_and_name(obj):
    """Tries to get the definition file and line of obj and its name"""
    source_info = _get_source_info(obj, None)
    if source_info is None:
        # NOTE(caselit): a class instances return None. Try the type
        source_info = _get_source_info(type(obj))
    name = getattr(obj, "__name__", None)
    if name is None:
        name = getattr(type(obj), "__name__", "[unknown]")
    return source_info, name


def _is_internal(obj):
    """Checks if the module of the object is a falcon module"""
    module = inspect.getmodule(obj)
    return module.__name__.startswith("falcon.")


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

                    source_info = _get_source_info(real_func)
                    internal = _is_internal(real_func)

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
        return "{} {} ({})".format(
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

    def as_string(self, verbose=False, indent=0):
        """Returns a string representation of this route

        Args:
            verbose (bool, optional): Print also internal routes. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this route
        """
        if verbose:
            methods = self.methods
        else:
            methods = [m for m in self.methods if not m.internal]
        tab = " " * indent
        text = "{}⇒ {}".format(tab, self.path)
        if not methods:
            return text

        c_tab = tab + " " * 2
        method_text = ["{}├── {}".format(c_tab, m) for m in methods[:-1]]
        method_text += ["{}└── {}".format(c_tab, m) for m in methods[-1:]]

        return "{}:\n{}".format(text, "\n".join(method_text))

    def __repr__(self):
        return self.as_string()


class StaticRouteInfo:
    """Utility class that contains the information of a static route

    Args:
        path (str): The prefix of the static route
        directory (str): The directory of this static route
        fallback_filename (str or None): Fallback filename to serve
    """

    def __init__(self, prefix, directory, fallback_filename):
        self.prefix = prefix
        self.directory = directory
        self.fallback_filename = fallback_filename

    def as_string(self, verbose=False, indent=0):
        """Returns a string representation of this static route

        Args:
            verbose (bool, optional): Currently unused. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this route
        """
        text = "{}↦ {} {}".format(" " * indent, self.prefix, self.directory)
        if self.fallback_filename:
            text += " ({})".format(self.fallback_filename)

        return text

    def __repr__(self):
        return self.as_string()


class AppInfo:
    """Utility class that contains the information of an application

    Args:
        routes (List[RouteInfo]): The routes of the application
        static_routes (List[StaticRouteInfo]): The static routes of this application
        sinks (List[SinkInfo]): The sinks of this application
        error_handlers (List[ErrorHandlerInfo]): The error handlers of this application
    """

    def __init__(self, routes, static_routes, sinks, error_handlers):
        self.routes = routes
        self.static_routes = static_routes
        self.sinks = sinks
        self.error_handlers = error_handlers

    def as_string(self, verbose=False, name="Falcon App"):
        """Returns a string representation of this app

        Args:
            verbose (bool, optional): Prints more informations. Defaults to False.
            name (str, optional): The name of the application. Will be places at the
                beginning of the text. Defaults to 'Falcon App'
        Returns:
            str: string representation of the application
        """
        indent = 4
        text = "{}".format(name)

        if self.routes:
            routes = "\n".join(r.as_string(verbose, indent) for r in self.routes)
            text += "\n• Routes:\n{}".format(routes)

        if self.static_routes:
            static_routes = "\n".join(
                sr.as_string(verbose, indent) for sr in self.static_routes
            )
            text += "\n• Static routes:\n{}".format(static_routes)

        if self.sinks:
            sinks = "\n".join(s.as_string(verbose, indent) for s in self.sinks)
            text += "\n• Sinks:\n{}".format(sinks)

        errors = self.error_handlers
        if not verbose:
            errors = [e for e in self.error_handlers if not e.internal]
        if errors:
            errs = "\n".join(e.as_string(verbose, indent) for e in errors)
            text += "\n• Error handlers:\n{}".format(errs)

        if text.startswith("\n"):
            # NOTE(caselit): if name is empty text will start with a new line
            return text[1:]
        return text

    def __repr__(self):
        return self.as_string()


class SinkInfo:
    """Utility class that contains the information of a sink

    Args:
        prefix (str): The prefix of the sink
        name (str): The name of the sink function or class
        source_info (str): The source path where this sink was defined
    """

    def __init__(self, prefix, name, source_info):
        self.prefix = prefix
        self.name = name
        self.source_info = source_info

    def as_string(self, verbose=False, indent=0):
        """Returns a string representation of this sink

        Args:
            verbose (bool, optional): Currently unused. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this sink
        """
        text = "{}⇥ {} {} ({})".format(
            " " * indent, self.prefix, self.name, self.source_info
        )
        return text

    def __repr__(self):
        return self.as_string()


class ErrorHandlerInfo:
    """Utility class that contains the information of an error handler

    Args:
        error (name): The error it manages
        name (str): The name of the handler
        source_info (str): The source path where this error handler was defined
        internal (bool): If this error handler was added by falcon
    """

    def __init__(self, error, name, source_info, internal):
        self.error = error
        self.name = name
        self.source_info = source_info
        self.internal = internal

    def as_string(self, verbose=False, indent=0):
        """Returns a string representation of this sink

        Args:
            verbose (bool, optional): Currently unused. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this sink
        """
        text = "{}⇜ {} {} ({})".format(
            " " * indent, self.error, self.name, self.source_info
        )
        return text

    def __repr__(self):
        return self.as_string()
