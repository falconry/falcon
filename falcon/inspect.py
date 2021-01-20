# Copyright 2020 by Federico Caselli
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

"""Inspect utilities for falcon applications."""
from functools import partial
import inspect
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

from falcon import app_helpers
from falcon.app import App
from falcon.routing import CompiledRouter


def inspect_app(app: App) -> 'AppInfo':
    """Inspects an application.

    Args:
        app (falcon.App): The application to inspect. Works with both
            :class:`falcon.App` and :class:`falcon.asgi.App`.

    Returns:
        AppInfo: The information regarding the application. Call
        :meth:`~.AppInfo.to_string` on the result to obtain a human-friendly
        representation.
    """
    routes = inspect_routes(app)
    static = inspect_static_routes(app)
    sinks = inspect_sinks(app)
    error_handlers = inspect_error_handlers(app)
    middleware = inspect_middleware(app)
    return AppInfo(routes, middleware, static, sinks, error_handlers, app._ASGI)


def inspect_routes(app: App) -> 'List[RouteInfo]':
    """Inspects the routes of an application.

    Args:
        app (falcon.App): The application to inspect. Works with both
            :class:`falcon.App` and :class:`falcon.asgi.App`.

    Returns:
        List[RouteInfo]: A list of route descriptions for the application.
    """
    router = app._router

    inspect_function = _supported_routers.get(type(router))
    if inspect_function is None:
        raise TypeError(
            'Unsupported router class {}. Use "register_router" '
            'to register a function that can inspect the router '
            'used by the provided application'.format(type(router))
        )
    return inspect_function(router)


def register_router(router_class):
    """Register a function to inspect a particular router.

    This decorator registers a new function for a custom router
    class, so that it can be inspected with the function
    :func:`.inspect_routes`.
    An inspection function takes the router instance used by the
    application and returns a list of :class:`.RouteInfo`. Eg::

        @register_router(MyRouterClass)
        def inspect_my_router(router):
            return [RouteInfo('foo', 'bar', '/path/to/foo.py:42', [])]

    Args:
        router_class (Type): The router class to register. If
            already registered an error will be raised.
    """

    def wraps(fn):
        if router_class in _supported_routers:
            raise ValueError(
                'Another function is already registered'
                ' for the router {}'.format(router_class)
            )
        _supported_routers[router_class] = fn
        return fn

    return wraps


# router inspection registry
_supported_routers = {}  # type: Dict[Type, Callable]


def inspect_static_routes(app: App) -> 'List[StaticRouteInfo]':
    """Inspects the static routes of an application.

    Args:
        app (falcon.App): The application to inspect. Works with both
            :class:`falcon.App` and :class:`falcon.asgi.App`.

    Returns:
        List[StaticRouteInfo]: A list of static routes that have
        been added to the application.
    """
    routes = []
    for sr, _, _ in app._static_routes:
        info = StaticRouteInfo(sr._prefix, sr._directory, sr._fallback_filename)
        routes.append(info)
    return routes


def inspect_sinks(app: App) -> 'List[SinkInfo]':
    """Inspects the sinks of an application.

    Args:
        app (falcon.App): The application to inspect. Works with both
            :class:`falcon.App` and :class:`falcon.asgi.App`.

    Returns:
        List[SinkInfo]: A list of sinks used by the application.
    """
    sinks = []
    for prefix, sink, _ in app._sinks:
        source_info, name = _get_source_info_and_name(sink)
        info = SinkInfo(prefix.pattern, name, source_info)
        sinks.append(info)
    return sinks


def inspect_error_handlers(app: App) -> 'List[ErrorHandlerInfo]':
    """Inspects the error handlers of an application.

    Args:
        app (falcon.App): The application to inspect. Works with both
            :class:`falcon.App` and :class:`falcon.asgi.App`.

    Returns:
        List[ErrorHandlerInfo]: A list of error handlers used by the
        application.
    """
    errors = []
    for exc, fn in app._error_handlers.items():
        source_info, name = _get_source_info_and_name(fn)
        info = ErrorHandlerInfo(exc.__name__, name, source_info, _is_internal(fn))
        errors.append(info)
    return errors


def inspect_middleware(app: App) -> 'MiddlewareInfo':
    """Inspects the middleware components of an application.

    Args:
        app (falcon.App): The application to inspect. Works with both
            :class:`falcon.App` and :class:`falcon.asgi.App`.

    Returns:
        MiddlewareInfo: Information about the app's middleware components.
    """
    types_ = app_helpers.prepare_middleware(app._unprepared_middleware, True, app._ASGI)

    type_infos = []
    for stack in types_:
        current = []
        for method in stack:
            _, name = _get_source_info_and_name(method)
            cls = type(method.__self__)
            _, cls_name = _get_source_info_and_name(cls)
            current.append(MiddlewareTreeItemInfo(name, cls_name))
        type_infos.append(current)
    middlewareTree = MiddlewareTreeInfo(*type_infos)

    middlewareClasses = []
    names = 'Process request', 'Process resource', 'Process response'
    for m in app._unprepared_middleware:
        fns = app_helpers.prepare_middleware([m], True, app._ASGI)
        class_source_info, cls_name = _get_source_info_and_name(type(m))
        methods = []
        for method, name in zip(fns, names):
            if method:
                real_func = method[0]
                source_info = _get_source_info(real_func)
                methods.append(MiddlewareMethodInfo(real_func.__name__, source_info))
        m_info = MiddlewareClassInfo(cls_name, class_source_info, methods)
        middlewareClasses.append(m_info)

    return MiddlewareInfo(
        middlewareTree, middlewareClasses, app._independent_middleware
    )


@register_router(CompiledRouter)
def inspect_compiled_router(router: CompiledRouter) -> 'List[RouteInfo]':
    """Walk an instance of :class:`~.CompiledRouter` to return a list of defined routes.

    Default route inspector for CompiledRouter.

    Args:
        router (CompiledRouter): The router to inspect.

    Returns:
        List[RouteInfo]: A list of :class:`~.RouteInfo`.
    """

    def _traverse(roots, parent):
        for root in roots:
            path = parent + '/' + root.raw_segment
            if root.resource is not None:
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

                route_info = RouteInfo(path, class_name, source_info, methods)
                routes.append(route_info)

            if root.children:
                _traverse(root.children, path)

    routes = []  # type: List[RouteInfo]
    _traverse(router._roots, '')
    return routes


# ------------------------------------------------------------------------
# Inspection classes
# ------------------------------------------------------------------------


class _Traversable:
    __visit_name__ = 'N/A'

    def to_string(self, verbose=False, internal=False) -> str:
        """Return a string representation of this class.

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            internal (bool, optional): Also include internal route methods
                and error handlers added by the framework. Defaults to
                ``False``.

        Returns:
            str: string representation of this class.
        """
        return StringVisitor(verbose, internal).process(self)

    def __repr__(self):
        return self.to_string()


class RouteMethodInfo(_Traversable):
    """Describes a responder method.

    Args:
        method (str): The HTTP method of this responder.
        source_info (str): The source path of this function.
        function_name (str): Name of the function.
        internal (bool): Whether or not this was a default responder added
            by the framework.

    Attributes:
        suffix (str): The suffix of this route function. This is set to an empty
            string when the function has no suffix.
    """

    __visit_name__ = 'route_method'

    def __init__(
        self, method: str, source_info: str, function_name: str, internal: bool
    ):
        self.method = method
        self.source_info = source_info
        self.function_name = function_name
        self.internal = internal
        # NOTE(CaselIT): internal falcon names do not start with on and do not have suffix
        if function_name.startswith('on'):
            self.suffix = '_'.join(function_name.split('_')[2:])
        else:
            self.suffix = ''


class RouteInfo(_Traversable):
    """Describes a route.

    Args:
        path (str): The path of this route.
        class_name (str): The class name of the responder of this route.
        source_info (str): The source path where this responder was defined.
        methods (List[RouteMethodInfo]): List of methods defined in the route.
    """

    __visit_name__ = 'route'

    def __init__(
        self,
        path: str,
        class_name: str,
        source_info: str,
        methods: List[RouteMethodInfo],
    ):
        self.path = path
        self.class_name = class_name
        self.source_info = source_info
        self.methods = methods


class StaticRouteInfo(_Traversable):
    """Describes a static route.

    Args:
        path (str): The prefix of the static route.
        directory (str): The directory for the static route.
        fallback_filename (str or None): Fallback filename to serve.
    """

    __visit_name__ = 'static_route'

    def __init__(self, prefix: str, directory: str, fallback_filename: Optional[str]):
        self.prefix = prefix
        self.directory = directory
        self.fallback_filename = fallback_filename


class SinkInfo(_Traversable):
    """Describes a sink.

    Args:
        prefix (str): The prefix of the sink.
        name (str): The name of the sink function or class.
        source_info (str): The source path where this sink was defined.
    """

    __visit_name__ = 'sink'

    def __init__(self, prefix: str, name: str, source_info: str):
        self.prefix = prefix
        self.name = name
        self.source_info = source_info


class ErrorHandlerInfo(_Traversable):
    """Desribes an error handler.

    Args:
        error (name): The name of the error type.
        name (str): The name of the handler.
        source_info (str): The source path where this error handler was defined.
        internal (bool): Whether or not this is a default error handler added by
            the framework.
    """

    __visit_name__ = 'error_handler'

    def __init__(self, error: str, name: str, source_info: str, internal: bool):
        self.error = error
        self.name = name
        self.source_info = source_info
        self.internal = internal


class MiddlewareMethodInfo(_Traversable):
    """Describes a middleware method.

    Args:
        function_name (str): Name of the method.
        source_info (str): The source path of the method.
    """

    __visit_name__ = 'middleware_method'

    def __init__(self, function_name: str, source_info: str):
        self.function_name = function_name
        self.source_info = source_info
        self.internal = False  # added for compatibility with RouteMethodInfo


class MiddlewareClassInfo(_Traversable):
    """Describes a middleware class.

    Args:
        name (str): The name of the middleware class.
        source_info (str): The source path where the middleware was defined.
        methods (List[MiddlewareMethodInfo]): List of method defined by the middleware class.
    """

    __visit_name__ = 'middleware_class'

    def __init__(
        self, name: str, source_info: str, methods: List[MiddlewareMethodInfo]
    ):
        self.name = name
        self.source_info = source_info
        self.methods = methods


class MiddlewareTreeItemInfo(_Traversable):
    """Describes a middleware tree entry.

    Args:
        name (str): The name of the method.
        class_name (str): The class name of the method.
    """

    __visit_name__ = 'middleware_tree_item'

    _symbols = {
        'process_request': '→',
        'process_resource': '↣',
        'process_response': '↢',
    }

    def __init__(self, name: str, class_name: str):
        self.name = name
        self.class_name = class_name


class MiddlewareTreeInfo(_Traversable):
    """Describes the middleware methods used by the app.

    Args:
        request (List[MiddlewareTreeItemInfo]): The `process_request` methods.
        resource (List[MiddlewareTreeItemInfo]): The `process_resource` methods.
        response (List[MiddlewareTreeItemInfo]): The `process_response` methods.
    """

    __visit_name__ = 'middleware_tree'

    def __init__(
        self,
        request: List[MiddlewareTreeItemInfo],
        resource: List[MiddlewareTreeItemInfo],
        response: List[MiddlewareTreeItemInfo],
    ):
        self.request = request
        self.resource = resource
        self.response = response


class MiddlewareInfo(_Traversable):
    """Describes the middleware of the app.

    Args:
        middlewareTree (MiddlewareTreeInfo): The middleware tree of the app.
        middlewareClasses (List[MiddlewareClassInfo]): The middleware classes of the app.
        independent (bool): Whether or not the middleware components are executed
            independently.

    Attributes:
        independent_text (str): Text created from the `independent` arg.
    """

    __visit_name__ = 'middleware'

    def __init__(
        self,
        middleware_tree: MiddlewareTreeInfo,
        middleware_classes: List[MiddlewareClassInfo],
        independent: bool,
    ):
        self.middleware_tree = middleware_tree
        self.middleware_classes = middleware_classes
        self.independent = independent

        if independent:
            self.independent_text = 'Middleware are independent'
        else:
            self.independent_text = 'Middleware are dependent'


class AppInfo(_Traversable):
    """Describes an application.

    Args:
        routes (List[RouteInfo]): The routes of the application.
        middleware (MiddlewareInfo): The middleware information in the application.
        static_routes (List[StaticRouteInfo]): The static routes of this application.
        sinks (List[SinkInfo]): The sinks of this application.
        error_handlers (List[ErrorHandlerInfo]): The error handlers of this application.
        asgi (bool): Whether or not this is an ASGI application.
    """

    __visit_name__ = 'app'

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

    def to_string(self, verbose=False, internal=False, name='') -> str:
        """Return a string representation of this class.

        Args:
            verbose (bool, optional): Adds more information. Defaults to False.
            internal (bool, optional): Also include internal falcon route methods
                and error handlers. Defaults to ``False``.
            name (str, optional): The name of the application, to be output at the
                beginning of the text. Defaults to ``'Falcon App'``.
        Returns:
            str: A string representation of the application.
        """
        return StringVisitor(verbose, internal, name).process(self)


# ------------------------------------------------------------------------
# Visitor classes
# ------------------------------------------------------------------------


class InspectVisitor:
    """Base visitor class that implements the `process` method.

    Subclasses must implement ``visit_<name>`` methods for each supported class.
    """

    def process(self, instance: _Traversable):
        """Process the instance, by calling the appropriate visit method.

        Uses the `__visit_name__` attribute of the `instance` to obtain the method to use.

        Args:
            instance (_Traversable): The instance to process.
        """
        try:
            return getattr(self, 'visit_{}'.format(instance.__visit_name__))(instance)
        except AttributeError as e:
            raise RuntimeError(
                'This visitor does not support {}'.format(type(instance))
            ) from e


class StringVisitor(InspectVisitor):
    """Visitor that returns a string representation of the info class.

    This is used automatically by calling ``to_string()`` on the info class.
    It can also be used directly by calling ``StringVisitor.process(info_instance)``.

    Args:
        verbose (bool, optional): Adds more information. Defaults to ``False``.
        internal (bool, optional): Also include internal route methods
            and error handlers added by the framework. Defaults to ``False``.
        name (str, optional): The name of the application, to be output at the
            beginning of the text. Defaults to ``'Falcon App'``.
    """

    def __init__(self, verbose=False, internal=False, name=''):
        self.verbose = verbose
        self.internal = internal
        self.name = name
        self.indent = 0

    @property
    def tab(self):
        """Get the current tabulation."""
        return ' ' * self.indent

    def visit_route_method(self, route_method: RouteMethodInfo) -> str:
        """Visit a RouteMethodInfo instance. Usually called by `process`."""
        text = '{0.method} - {0.function_name}'.format(route_method)
        if self.verbose:
            text += ' ({0.source_info})'.format(route_method)
        return text

    def _methods_to_string(self, methods: List):
        """Return a string from the list of methods."""
        tab = self.tab + ' ' * 3
        methods = _filter_internal(methods, self.internal)
        if not methods:
            return ''
        text_list = [self.process(m) for m in methods]
        method_text = ['{}├── {}'.format(tab, m) for m in text_list[:-1]]
        method_text += ['{}└── {}'.format(tab, m) for m in text_list[-1:]]
        return '\n'.join(method_text)

    def visit_route(self, route: RouteInfo) -> str:
        """Visit a RouteInfo instance. Usually called by `process`."""
        text = '{0}⇒ {1.path} - {1.class_name}'.format(self.tab, route)
        if self.verbose:
            text += ' ({0.source_info})'.format(route)

        method_text = self._methods_to_string(route.methods)
        if not method_text:
            return text

        return '{}:\n{}'.format(text, method_text)

    def visit_static_route(self, static_route: StaticRouteInfo) -> str:
        """Visit a StaticRouteInfo instance. Usually called by `process`."""
        text = '{0}↦ {1.prefix} {1.directory}'.format(self.tab, static_route)
        if static_route.fallback_filename:
            text += ' [{0.fallback_filename}]'.format(static_route)
        return text

    def visit_sink(self, sink: SinkInfo) -> str:
        """Visit a SinkInfo instance. Usually called by `process`."""
        text = '{0}⇥ {1.prefix} {1.name}'.format(self.tab, sink)
        if self.verbose:
            text += ' ({0.source_info})'.format(sink)
        return text

    def visit_error_handler(self, error_handler: ErrorHandlerInfo) -> str:
        """Visit a ErrorHandlerInfo instance. Usually called by `process`."""
        text = '{0}⇜ {1.error} {1.name}'.format(self.tab, error_handler)
        if self.verbose:
            text += ' ({0.source_info})'.format(error_handler)
        return text

    def visit_middleware_method(self, middleware_method: MiddlewareMethodInfo) -> str:
        """Visit a MiddlewareMethodInfo instance. Usually called by `process`."""
        text = '{0.function_name}'.format(middleware_method)
        if self.verbose:
            text += ' ({0.source_info})'.format(middleware_method)
        return text

    def visit_middleware_class(self, middleware_class: MiddlewareClassInfo) -> str:
        """Visit a ErrorHandlerInfo instance. Usually called by `process`."""
        text = '{0}↣ {1.name}'.format(self.tab, middleware_class)
        if self.verbose:
            text += ' ({0.source_info})'.format(middleware_class)

        method_text = self._methods_to_string(middleware_class.methods)
        if not method_text:
            return text

        return '{}:\n{}'.format(text, method_text)

    def visit_middleware_tree_item(self, mti: MiddlewareTreeItemInfo) -> str:
        """Visit a MiddlewareTreeItemInfo instance. Usually called by `process`."""
        symbol = mti._symbols.get(mti.name, '→')
        return '{0}{1} {2.class_name}.{2.name}'.format(self.tab, symbol, mti)

    def visit_middleware_tree(self, m_tree: MiddlewareTreeInfo) -> str:
        """Visit a MiddlewareTreeInfo instance. Usually called by `process`."""
        before = len(m_tree.request) + len(m_tree.resource)
        after = len(m_tree.response)

        if before + after == 0:
            return ''

        each = 2
        initial = self.indent
        if after > before:
            self.indent += each * (after - before)

        text = []
        for r in m_tree.request:
            text.append(self.process(r))
            self.indent += each
        if text:
            text.append('')
        for r in m_tree.resource:
            text.append(self.process(r))
            self.indent += each

        if m_tree.resource or not text:
            text.append('')
        self.indent += each
        text.append('{}├── Process route responder'.format(self.tab))
        self.indent -= each
        if m_tree.response:
            text.append('')

        for r in m_tree.response:
            self.indent -= each
            text.append(self.process(r))

        self.indent = initial
        return '\n'.join(text)

    def visit_middleware(self, middleware: MiddlewareInfo) -> str:
        """Visit a MiddlewareInfo instance. Usually called by `process`."""
        text = self.process(middleware.middleware_tree)
        if self.verbose:
            self.indent += 4
            m_text = '\n'.join(self.process(m) for m in middleware.middleware_classes)
            self.indent -= 4
            if m_text:
                text += '\n{}- Middleware classes:\n{}'.format(self.tab, m_text)

        return text

    def visit_app(self, app: AppInfo) -> str:
        """Visit a AppInfo instance. Usually called by `process`."""

        type_ = 'ASGI' if app.asgi else 'WSGI'
        self.indent = 4
        text = '{} ({})'.format(self.name or 'Falcon App', type_)

        if app.routes:
            routes = '\n'.join(self.process(r) for r in app.routes)
            text += '\n• Routes:\n{}'.format(routes)

        middleware_text = self.process(app.middleware)
        if middleware_text:
            text += '\n• Middleware ({}):\n{}'.format(
                app.middleware.independent_text, middleware_text
            )

        if app.static_routes:
            static_routes = '\n'.join(self.process(sr) for sr in app.static_routes)
            text += '\n• Static routes:\n{}'.format(static_routes)

        if app.sinks:
            sinks = '\n'.join(self.process(s) for s in app.sinks)
            text += '\n• Sinks:\n{}'.format(sinks)

        errors = _filter_internal(app.error_handlers, self.internal)
        if errors:
            errs = '\n'.join(self.process(e) for e in errors)
            text += '\n• Error handlers:\n{}'.format(errs)

        return text


# ------------------------------------------------------------------------
# Helpers functions
# ------------------------------------------------------------------------


def _get_source_info(obj, default='[unknown file]'):
    """Try to get the definition file and line of obj.

     Return default on error.
     """
    try:
        source_file = inspect.getsourcefile(obj)
        source_lines = inspect.findsource(obj)
        source_info = '{}:{}'.format(source_file, source_lines[1])
    except Exception:
        # NOTE(vytas): If Falcon is cythonized, all default
        # responders coming from cythonized modules will
        # appear as built-in functions, and raise a
        # TypeError when trying to locate the source file.
        source_info = default
    return source_info


def _get_source_info_and_name(obj):
    """Attempt to get the definition file and line of obj and its name."""
    source_info = _get_source_info(obj, None)
    if source_info is None:
        # NOTE(caselit): a class instances return None. Try the type
        source_info = _get_source_info(type(obj))
    name = getattr(obj, '__name__', None)
    if name is None:
        name = getattr(type(obj), '__name__', '[unknown]')
    return source_info, name


def _is_internal(obj):
    """Check if the module of the object is a falcon module."""
    module = inspect.getmodule(obj)
    if module:
        return module.__name__.startswith('falcon.')
    return False


def _filter_internal(iterable, return_internal):
    """Filter the internal elements of an iterable."""
    if return_internal:
        return iterable
    return [el for el in iterable if not el.internal]
