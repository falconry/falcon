"""Inspect utilities for falcon applications"""
import inspect
from functools import partial
from typing import List, Optional

from falcon import App, app_helpers
from falcon.routing import CompiledRouter


def inspect_app(app: App) -> "AppInfo":
    """Inspects an application

    Args:
        app (App): The application to inspect

    Returns:
        AppInfo: The information regarding the application.
            Call the ``to_string`` to obtain a string representation of it
    """
    routes = inspect_routes(app)
    static = inspect_static_routes(app)
    sinks = inspect_sinks(app)
    error_handlers = inspect_error_handlers(app)
    middleware = inspect_middlewares(app)
    return AppInfo(routes, middleware, static, sinks, error_handlers, app._ASGI,)


def inspect_routes(app: App) -> "List[RouteInfo]":
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


def inspect_static_routes(app: App) -> "List[StaticRouteInfo]":
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


def inspect_sinks(app: App) -> "List[SinkInfo]":
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


def inspect_error_handlers(app: App) -> "List[ErrorHandlerInfo]":
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


def inspect_middlewares(app: App) -> "MiddlewareInfo":
    """Inspects the meddlewares of an application

    Args:
        app (App): The application to inspect

    Returns:
        MiddlewareInfo: The information of the middlewares
    """
    types_ = app_helpers.prepare_middleware(app._unprepared_middleware, True, app._ASGI)

    type_infos = []
    for stack in types_:
        current = []
        for method in stack:
            _, name = _get_source_info_and_name(method)
            cls = type(method.__self__)
            _, cls_name = _get_source_info_and_name(cls)
            info = MiddlewareTreeItemInfo(name, cls_name)
            current.append(info)
        type_infos.append(current)
    middlewareTree = MiddlewareTreeInfo(*type_infos)

    middlewareClasses = []
    names = "Process request", "Process resource", "Process response"
    for m in app._unprepared_middleware:
        fns = app_helpers.prepare_middleware([m], True, app._ASGI)
        class_source_info, cls_name = _get_source_info_and_name(type(m))
        methods = []
        for method, name in zip(fns, names):
            if method:
                real_func = method[0]
                source_info = _get_source_info(real_func)
                info = MiddlewareMethodInfo(real_func.__name__, source_info)
                methods.append(info)
        m_info = MeddlewareClassInfo(cls_name, class_source_info, methods)
        middlewareClasses.append(m_info)

    return MiddlewareInfo(
        middlewareTree, middlewareClasses, app._independent_middleware
    )


@register_router(CompiledRouter)
def inspect_compiled_router(router) -> "List[RouteInfo]":
    """Expores the compiled router and returns the list of defined routes

    Args:
        router (CompiledRouter): The router to inspect

    Returns
        List[RouteInfo]: A list of RouteInfo
    """

    def _traverse(roots, parent):
        for root in roots:
            methods = []
            if root.method_map:
                for method, func in root.method_map.items():
                    if isinstance(func, partial):
                        real_func = func.func
                    else:
                        real_func = func

                    source_info = _get_source_info(real_func)
                    internal = _is_internal(real_func)

                    method_info = RouteMethodInfo(
                        method, source_info, real_func.__name__, internal
                    )
                    methods.append(method_info)
                source_info, class_name = _get_source_info_and_name(root.resource)

            path = parent + "/" + root.raw_segment
            route_info = RouteInfo(path, class_name, source_info, methods)
            routes.append(route_info)

            if root.children:
                _traverse(root.children, path)

    routes = []
    _traverse(router._roots, "")
    return routes


# ------------------------------------------------------------------------
# Inspection classes functions
# ------------------------------------------------------------------------


class RouteMethodInfo:
    """Utility class that contains the description of a responder method

    Args:
        method (str): The http method of this responder
        source_info (str): The source path of this function
        function_name (str): Name of the function
        internal (bool): If this responder was added by falcon
    """

    def __init__(
        self, method: str, source_info: str, function_name: str, internal: bool
    ):
        self.method = method
        self.source_info = source_info
        self.function_name = function_name
        self.internal = internal

    def to_string(self, verbose=False) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.

        Returns:
            str: string representation of this class
        """
        text = "{} - {}".format(self.method, self.function_name)
        if verbose:
            text += " ({})".format(self.source_info)
        return text

    def __repr__(self):
        return self.to_string()


class _WithMethods:
    """Common superclass with methods"""

    def __init__(self, methods: list):
        self.methods = methods

    def _methods_to_string(self, verbose: bool, indent: int):
        """Returns a string from the list of methods"""
        tab = " " * indent + " " * 3
        methods = _filter_internal(self.methods, verbose)
        if not methods:
            return ""
        text_list = [m.to_string(verbose) for m in methods]
        method_text = ["{}├── {}".format(tab, m) for m in text_list[:-1]]
        method_text += ["{}└── {}".format(tab, m) for m in text_list[-1:]]
        return "\n".join(method_text)


class RouteInfo(_WithMethods):
    """Utility class that contains the information of a route

    Args:
        path (str): The path of this route
        class_name (str): The class name of the responder of this route
        source_info (str): The source path where this responder was defined
        methods (List[MethodInfo]): List of method defined in the route
    """

    def __init__(
        self,
        path: str,
        class_name: str,
        source_info: str,
        methods: List[RouteMethodInfo],
    ):
        super().__init__(methods)
        self.path = path
        self.class_name = class_name
        self.source_info = source_info

    def to_string(self, verbose=False, indent=0) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this class
        """
        tab = " " * indent
        text = "{}⇒ {} - {}".format(tab, self.path, self.class_name)
        if verbose:
            text += " ({})".format(self.source_info)

        method_text = self._methods_to_string(verbose, indent)
        if not method_text:
            return text

        return "{}:\n{}".format(text, method_text)

    def __repr__(self):
        return self.to_string()


class StaticRouteInfo:
    """Utility class that contains the information of a static route

    Args:
        path (str): The prefix of the static route
        directory (str): The directory of this static route
        fallback_filename (str or None): Fallback filename to serve
    """

    def __init__(self, prefix: str, directory: str, fallback_filename: Optional[str]):
        self.prefix = prefix
        self.directory = directory
        self.fallback_filename = fallback_filename

    def to_string(self, verbose=False, indent=0) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this class
        """
        text = "{}↦ {} {}".format(" " * indent, self.prefix, self.directory)
        if self.fallback_filename:
            text += " [{}]".format(self.fallback_filename)

        return text

    def __repr__(self):
        return self.to_string()


class SinkInfo:
    """Utility class that contains the information of a sink

    Args:
        prefix (str): The prefix of the sink
        name (str): The name of the sink function or class
        source_info (str): The source path where this sink was defined
    """

    def __init__(self, prefix: str, name: str, source_info: str):
        self.prefix = prefix
        self.name = name
        self.source_info = source_info

    def to_string(self, verbose=False, indent=0) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this class
        """
        text = "{}⇥ {} {}".format(" " * indent, self.prefix, self.name)
        if verbose:
            text += " ({})".format(self.source_info)
        return text

    def __repr__(self):
        return self.to_string()


class ErrorHandlerInfo:
    """Utility class that contains the information of an error handler

    Args:
        error (name): The error it manages
        name (str): The name of the handler
        source_info (str): The source path where this error handler was defined
        internal (bool): If this error handler was added by falcon
    """

    def __init__(self, error: str, name: str, source_info: str, internal: str):
        self.error = error
        self.name = name
        self.source_info = source_info
        self.internal = internal

    def to_string(self, verbose=False, indent=0) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this class
        """
        text = "{}⇜ {} {}".format(" " * indent, self.error, self.name)
        if verbose:
            text += " ({})".format(self.source_info)
        return text

    def __repr__(self):
        return self.to_string()


class MiddlewareMethodInfo:
    """Utility class that contains the description of a middleware method

    Args:
        function_name (str): Name of the method
        source_info (str): The source path of this function
    """

    def __init__(self, function_name: str, source_info: str):
        self.function_name = function_name
        self.source_info = source_info

    def to_string(self, verbose=False) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.

        Returns:
            str: string representation of this class
        """
        text = "{}".format(self.function_name)
        if verbose:
            text += " ({})".format(self.source_info)
        return text

    def __repr__(self):
        return self.to_string()


class MeddlewareClassInfo(_WithMethods):
    """Utility class that contains the information of a middleware class

    Args:
        name (str): The name of this middleware
        source_info (str): The source path where this middleware was defined
        methods (List[MiddlewareMethodInfo]): List of method defined in the middleware
    """

    def __init__(
        self, name: str, source_info: str, methods: List[MiddlewareMethodInfo]
    ):
        super().__init__(methods)
        self.name = name
        self.source_info = source_info

    def to_string(self, verbose=False, indent=0) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this class
        """
        tab = " " * indent
        text = "{}↣ {}".format(tab, self.name)
        if verbose:
            text += " ({})".format(self.source_info)

        method_text = self._methods_to_string(verbose, indent)
        if not method_text:
            return text

        return "{}:\n{}".format(text, method_text)

    def __repr__(self):
        return self.to_string()


class MiddlewareTreeItemInfo:
    """Utility class that contains the information of a middleware tree entry

    Args:
        name (str): The name of the method
        class_name (str): The class name of this method
    """

    def __init__(self, name: str, class_name: str):
        self.name = name
        self.class_name = class_name

    def to_string(self, symbol, verbose=False, indent=0) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this class
        """
        text = "{}{} {}.{}".format(" " * indent, symbol, self.class_name, self.name)
        return text


class MiddlewareTreeInfo:
    """Utility class that contains the information of the middleware methods used by the app

    Args:
        request (List[MiddlewareTreeItemInfo]): The process_request methods
        resource (List[MiddlewareTreeItemInfo]): The process_resource methods
        response (List[MiddlewareTreeItemInfo]): The process_response methods
    """

    def __init__(
        self,
        request: List[MiddlewareTreeItemInfo],
        resource: List[MiddlewareTreeItemInfo],
        response: List[MiddlewareTreeItemInfo],
    ):
        self.request = request
        self.resource = resource
        self.response = response

    def to_string(self, verbose=False, indent=0) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            indent (int, optional): Number of indentation spaces of the text. Defaults to 0.

        Returns:
            str: string representation of this class
        """
        before = len(self.request) + len(self.resource)
        after = len(self.response)

        each = 2
        initial = indent
        if after > before:
            initial += each * (after - before)

        current = initial
        text = []
        for r in self.request:
            text.append(r.to_string("→", verbose, current))
            current += each
        if text:
            text.append("")
        for r in self.resource:
            text.append(r.to_string("↣", verbose, current))
            current += each

        text.append("")

        text.append("{}├── Process responder".format(" " * (current + each)))
        if self.response:
            text.append("")

        for r in self.response:
            current -= each
            text.append(r.to_string("↢", verbose, current))

        return "\n".join(text)


class MiddlewareInfo:
    """Utility class that contains the information of the middleware of the app

    Args:
        middlewareTree (MiddlewareTreeInfo): The middleware tree of the app
        middlewareClasses (List[MeddlewareClassInfo]): The middleware classes of the app
        independent (bool): If the middleware are independent

    Attributes:
        independent_text (str): Text created from the ``independent`` arg
    """

    def __init__(
        self,
        middleware_tree: MiddlewareTreeInfo,
        middleware_classes: List[MeddlewareClassInfo],
        independent: bool,
    ):
        self.middleware_tree = middleware_tree
        self.middleware_classes = middleware_classes
        self.independent = independent

        if independent:
            self.independent_text = "Middleware are independent"
        else:
            self.independent_text = "Middleware are dependent"

    def to_string(self, verbose=False, indent=0) -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Prints more informations. Defaults to False.
            indent (int, optional): The indent to use. Defaults to 0.
        Returns:
            str: string representation of the application
        """
        text = self.middleware_tree.to_string(verbose, indent)
        if verbose:
            m_text = "\n".join(
                m.to_string(verbose, indent + 4) for m in self.middleware_classes
            )
            if m_text:
                text += "\n{}- Middlewares classes:\n{}".format(" " * indent, m_text)

        return text


class AppInfo:
    """Utility class that contains the information of an application

    Args:
        routes (List[RouteInfo]): The routes of the application
        middleware (MiddlewareInfo): The middleware information in the application
        static_routes (List[StaticRouteInfo]): The static routes of this application
        sinks (List[SinkInfo]): The sinks of this application
        error_handlers (List[ErrorHandlerInfo]): The error handlers of this application
        asgi (bool): If the application is ASGI
    """

    def __init__(
        self,
        routes: List[RouteInfo],
        middleware: MiddlewareInfo,
        static_routes: List[StaticRouteInfo],
        sinks: List[SinkInfo],
        error_handlers: List[ErrorHandlerInfo],
        asgi: bool,
    ):
        self.routes = routes
        self.middleware = middleware
        self.static_routes = static_routes
        self.sinks = sinks
        self.error_handlers = error_handlers
        self.asgi = asgi

    def to_string(self, verbose=False, name="") -> str:
        """Returns a string representation of this class

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            name (str, optional): The name of the application. Will be places at the
                beginning of the text. Will be 'Falcon App' when not provided
        Returns:
            str: string representation of the application
        """
        type_ = "ASGI" if self.asgi else "WSGI"
        indent = 4
        text = "{} ({})".format(name or "Falcon App", type_)

        if self.routes:
            routes = "\n".join(r.to_string(verbose, indent) for r in self.routes)
            text += "\n• Routes:\n{}".format(routes)

        middleware_text = self.middleware.to_string(verbose, indent)
        if middleware_text:
            text += "\n• Middleware ({}):\n{}".format(
                self.middleware.independent_text, middleware_text
            )

        if self.static_routes:
            static_routes = "\n".join(
                sr.to_string(verbose, indent) for sr in self.static_routes
            )
            text += "\n• Static routes:\n{}".format(static_routes)

        if self.sinks:
            sinks = "\n".join(s.to_string(verbose, indent) for s in self.sinks)
            text += "\n• Sinks:\n{}".format(sinks)

        errors = _filter_internal(self.error_handlers, verbose)
        if errors:
            errs = "\n".join(e.to_string(verbose, indent) for e in errors)
            text += "\n• Error handlers:\n{}".format(errs)

        return text

    def __repr__(self):
        return self.to_string()


# ------------------------------------------------------------------------
# Helpers functions
# ------------------------------------------------------------------------


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


def _filter_internal(iterable, return_internal):
    """Filters the internal elements of an iterable"""
    if return_internal:
        return iterable
    return [el for el in iterable if not el.internal]
