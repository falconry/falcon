from functools import partial
import os
import sys

import _inspect_fixture as i_f
import pytest

from falcon import inspect, routing


def get_app(asgi, cors=True, **kw):
    if asgi:
        from falcon.asgi import App as AsyncApp
        return AsyncApp(cors_enable=cors, **kw)
    else:
        from falcon import App
        return App(cors_enable=cors, **kw)


def make_app():
    app = get_app(False, cors=True)
    app.add_middleware(i_f.MyMiddleware())
    app.add_middleware(i_f.OtherMiddleware())

    app.add_sink(i_f.sinkFn, '/sink_fn')
    app.add_sink(i_f.SinkClass(), '/sink_cls')

    app.add_error_handler(RuntimeError, i_f.my_error_handler)

    app.add_route('/foo', i_f.MyResponder())
    app.add_route('/foo/{id}', i_f.MyResponder(), suffix='id')
    app.add_route('/bar', i_f.OtherResponder(), suffix='id')

    app.add_static_route('/fal', os.path.abspath('falcon'))
    app.add_static_route('/tes', os.path.abspath('tests'), fallback_filename='conftest.py')
    return app


def make_app_async():
    app = get_app(True, cors=True)
    app.add_middleware(i_f.MyMiddlewareAsync())
    app.add_middleware(i_f.OtherMiddlewareAsync())

    app.add_sink(i_f.sinkFn, '/sink_fn')
    app.add_sink(i_f.SinkClass(), '/sink_cls')

    app.add_error_handler(RuntimeError, i_f.my_error_handler_async)

    app.add_route('/foo', i_f.MyResponderAsync())
    app.add_route('/foo/{id}', i_f.MyResponderAsync(), suffix='id')
    app.add_route('/bar', i_f.OtherResponderAsync(), suffix='id')

    app.add_static_route('/fal', os.path.abspath('falcon'))
    app.add_static_route('/tes', os.path.abspath('tests'), fallback_filename='conftest.py')
    return app


class TestInspectApp:
    def test_empty_app(self, asgi):
        ai = inspect.inspect_app(get_app(asgi, False))

        assert ai.routes == []
        assert ai.middleware.middleware_tree.request == []
        assert ai.middleware.middleware_tree.resource == []
        assert ai.middleware.middleware_tree.response == []
        assert ai.middleware.middleware_classes == []
        assert ai.middleware.independent is True
        assert ai.static_routes == []
        assert ai.sinks == []
        assert len(ai.error_handlers) == 4 if asgi else 3
        assert ai.asgi is asgi

    def test_dependent_middleware(self, asgi):
        app = get_app(asgi, cors=False, independent_middleware=False)
        ai = inspect.inspect_app(app)
        assert ai.middleware.independent is False

    def test_app(self, asgi):
        ai = inspect.inspect_app(make_app_async() if asgi else make_app())

        assert len(ai.routes) == 3
        assert len(ai.middleware.middleware_tree.request) == 2
        assert len(ai.middleware.middleware_tree.resource) == 1
        assert len(ai.middleware.middleware_tree.response) == 3
        assert len(ai.middleware.middleware_classes) == 3
        assert len(ai.static_routes) == 2
        assert len(ai.sinks) == 2
        assert len(ai.error_handlers) == 5 if asgi else 4
        assert ai.asgi is asgi

    def check_route(self, asgi, r, p, cn, ml, fnt):
        assert isinstance(r, inspect.RouteInfo)
        assert r.path == p
        if asgi:
            cn += 'Async'
        assert r.class_name == cn
        assert '_inspect_fixture.py' in r.source_info

        for m in r.methods:
            assert isinstance(m, inspect.RouteMethodInfo)
            internal = '_inspect_fixture.py' not in m.source_info
            assert m.internal is internal
            if not internal:
                assert m.method in ml
                assert '_inspect_fixture.py' in m.source_info
                assert m.function_name == fnt.format(m.method).lower()

    def test_routes(self, asgi):
        routes = inspect.inspect_routes(make_app_async() if asgi else make_app())

        self.check_route(
            asgi, routes[0], '/foo', 'MyResponder', ['GET', 'POST', 'DELETE'], 'on_{}'
        )
        self.check_route(
            asgi, routes[1], '/foo/{id}', 'MyResponder', ['GET', 'PUT', 'DELETE'], 'on_{}_id'
        )
        self.check_route(asgi, routes[2], '/bar', 'OtherResponder', ['POST'], 'on_{}_id')

    def test_routes_empty_paths(self, asgi):
        app = get_app(asgi)
        r = i_f.MyResponderAsync() if asgi else i_f.MyResponder()
        app.add_route('/foo/bar/baz', r)

        routes = inspect.inspect_routes(app)

        assert len(routes) == 1

        self.check_route(
            asgi, routes[0], '/foo/bar/baz', 'MyResponder', ['GET', 'POST', 'DELETE'], 'on_{}'
        )

    def test_static_routes(self, asgi):
        routes = inspect.inspect_static_routes(make_app_async() if asgi else make_app())

        assert all(isinstance(sr, inspect.StaticRouteInfo) for sr in routes)
        assert routes[-1].prefix == '/fal/'
        assert routes[-1].directory == os.path.abspath('falcon')
        assert routes[-1].fallback_filename is None
        assert routes[-2].prefix == '/tes/'
        assert routes[-2].directory == os.path.abspath('tests')
        assert routes[-2].fallback_filename.endswith('conftest.py')

    def test_sink(self, asgi):
        sinks = inspect.inspect_sinks(make_app_async() if asgi else make_app())

        assert all(isinstance(s, inspect.SinkInfo) for s in sinks)
        assert sinks[-1].prefix == '/sink_fn'
        assert sinks[-1].name == 'sinkFn'
        if not asgi:
            assert '_inspect_fixture.py' in sinks[-1].source_info
        assert sinks[-2].prefix == '/sink_cls'
        assert sinks[-2].name == 'SinkClass'
        if not asgi:
            assert '_inspect_fixture.py' in sinks[-2].source_info

    @pytest.mark.skipif(sys.version_info < (3, 6), reason='dict order is not stable')
    def test_error_handler(self, asgi):
        errors = inspect.inspect_error_handlers(make_app_async() if asgi else make_app())

        assert all(isinstance(e, inspect.ErrorHandlerInfo) for e in errors)
        assert errors[-1].error == 'RuntimeError'
        assert errors[-1].name == 'my_error_handler_async' if asgi else 'my_error_handler'
        assert '_inspect_fixture.py' in errors[-1].source_info
        assert errors[-1].internal is False
        for eh in errors[:-1]:
            assert eh.internal
            assert eh.error in ('WebSocketDisconnected', 'Exception', 'HTTPStatus', 'HTTPError')

    def test_middleware(self, asgi):
        mi = inspect.inspect_middleware(make_app_async() if asgi else make_app())

        def test(m, cn, ml, inte):
            assert isinstance(m, inspect.MiddlewareClassInfo)
            assert m.name == cn
            if inte:
                assert '_inspect_fixture.py' not in m.source_info
            else:
                assert '_inspect_fixture.py' in m.source_info

            for mm in m.methods:
                assert isinstance(mm, inspect.MiddlewareMethodInfo)
                if inte:
                    assert '_inspect_fixture.py' not in mm.source_info
                else:
                    assert '_inspect_fixture.py' in mm.source_info
                assert mm.function_name in ml

        test(
            mi.middleware_classes[0],
            'CORSMiddleware',
            ['process_response_async'] if asgi else ['process_response'],
            True,
        )
        test(
            mi.middleware_classes[1],
            'MyMiddlewareAsync' if asgi else 'MyMiddleware',
            ['process_request', 'process_resource', 'process_response'],
            False,
        )
        test(
            mi.middleware_classes[2],
            'OtherMiddlewareAsync' if asgi else 'OtherMiddleware',
            ['process_request', 'process_resource', 'process_response'],
            False,
        )

    def test_middleware_tree(self, asgi):
        mi = inspect.inspect_middleware(make_app_async() if asgi else make_app())

        def test(tl, names, cls):
            for (t, n, c) in zip(tl, names, cls):
                assert isinstance(t, inspect.MiddlewareTreeItemInfo)
                assert t.name == n
                assert t.class_name == c

        assert isinstance(mi.middleware_tree, inspect.MiddlewareTreeInfo)

        test(
            mi.middleware_tree.request,
            ['process_request'] * 2,
            [n + 'Async' if asgi else n for n in ['MyMiddleware', 'OtherMiddleware']],
        )
        test(
            mi.middleware_tree.resource,
            ['process_resource'],
            ['MyMiddlewareAsync' if asgi else 'MyMiddleware'],
        )
        test(
            mi.middleware_tree.response,
            [
                'process_response',
                'process_response',
                'process_response_async' if asgi else 'process_response',
            ],
            [
                'OtherMiddlewareAsync' if asgi else 'OtherMiddleware',
                'MyMiddlewareAsync' if asgi else 'MyMiddleware',
                'CORSMiddleware',
            ],
        )


def test_route_method_info_suffix():
    ri = inspect.RouteMethodInfo('foo', '', 'on_get', False)
    assert ri.suffix == ''

    ri = inspect.RouteMethodInfo('foo', '', 'on_get_suffix', False)
    assert ri.suffix == 'suffix'

    ri = inspect.RouteMethodInfo('foo', '', 'on_get_multiple_underscores_suffix', False)
    assert ri.suffix == 'multiple_underscores_suffix'

    ri = inspect.RouteMethodInfo('foo', '', 'some_other_fn_name', False)
    assert ri.suffix == ''


class TestRouter:
    def test_compiled_partial(self):
        r = routing.CompiledRouter()
        r.add_route('/foo', i_f.MyResponder())
        # override a method with a partial
        r._roots[0].method_map['GET'] = partial(r._roots[0].method_map['GET'])
        ri = inspect.inspect_compiled_router(r)

        for m in ri[0].methods:
            if m.method == 'GET':
                assert '_inspect_fixture' in m.source_info

    def test_compiled_no_method_map(self):
        r = routing.CompiledRouter()
        r.add_route('/foo', i_f.MyResponder())
        # clear the method map
        r._roots[0].method_map.clear()
        ri = inspect.inspect_compiled_router(r)

        assert ri[0].path == '/foo'
        assert ri[0].class_name == 'MyResponder'
        assert ri[0].methods == []

    def test_register_router_not_found(self, monkeypatch):
        monkeypatch.setattr(inspect, '_supported_routers', {})

        app = get_app(False)
        with pytest.raises(TypeError, match='Unsupported router class'):
            inspect.inspect_routes(app)

    def test_register_other_router(self, monkeypatch):
        monkeypatch.setattr(inspect, '_supported_routers', {})

        app = get_app(False)
        app._router = i_f.MyRouter()

        @inspect.register_router(i_f.MyRouter)
        def print_routes(r):
            assert r is app._router
            return [inspect.RouteInfo('foo', 'bar', '', [])]

        ri = inspect.inspect_routes(app)

        assert ri[0].source_info == ''
        assert ri[0].path == 'foo'
        assert ri[0].class_name == 'bar'
        assert ri[0].methods == []

    def test_register_router_multiple_time(self, monkeypatch):
        monkeypatch.setattr(inspect, '_supported_routers', {})

        @inspect.register_router(i_f.MyRouter)
        def print_routes(r):
            return []

        with pytest.raises(ValueError, match='Another function is already registered'):
            @inspect.register_router(i_f.MyRouter)
            def print_routes2(r):
                return []


def test_info_class_repr_to_string():
    ai = inspect.inspect_app(make_app())

    assert str(ai) == ai.to_string()
    assert str(ai.routes[0]) == ai.routes[0].to_string()
    assert str(ai.routes[0].methods[0]) == ai.routes[0].methods[0].to_string()
    assert str(ai.middleware) == ai.middleware.to_string()
    s = str(ai.middleware.middleware_classes[0])
    assert s == ai.middleware.middleware_classes[0].to_string()
    s = str(ai.middleware.middleware_tree.request[0])
    assert s == ai.middleware.middleware_tree.request[0].to_string()
    assert str(ai.static_routes[0]) == ai.static_routes[0].to_string()
    assert str(ai.sinks[0]) == ai.sinks[0].to_string()
    assert str(ai.error_handlers[0]) == ai.error_handlers[0].to_string()


class TestInspectVisitor:
    def test_inspect_visitor(self):
        iv = inspect.InspectVisitor()
        with pytest.raises(RuntimeError, match='This visitor does not support'):
            iv.process(123)
        with pytest.raises(RuntimeError, match='This visitor does not support'):
            iv.process(inspect.RouteInfo('f', 'o', 'o', []))

    def test_process(self):
        class FooVisitor(inspect.InspectVisitor):
            def visit_route(self, route):
                return 'foo'

        assert FooVisitor().process(inspect.RouteInfo('f', 'o', 'o', [])) == 'foo'


def test_string_visitor_class():
    assert issubclass(inspect.StringVisitor, inspect.InspectVisitor)

    sv = inspect.StringVisitor()
    assert sv.verbose is False
    assert sv.internal is False
    assert sv.name == ''


@pytest.mark.parametrize('internal', (True, False))
class TestStringVisitor:

    def test_route_method(self, internal):
        sv = inspect.StringVisitor(False, internal)
        rm = inspect.inspect_routes(make_app())[0].methods[0]

        assert sv.process(rm) == '{0.method} - {0.function_name}'.format(rm)

    def test_route_method_verbose(self, internal):
        sv = inspect.StringVisitor(True, internal)
        rm = inspect.inspect_routes(make_app())[0].methods[0]

        assert sv.process(rm) == '{0.method} - {0.function_name} ({0.source_info})'.format(rm)

    def test_route(self, internal):
        sv = inspect.StringVisitor(False, internal)
        r = inspect.inspect_routes(make_app())[0]

        ml = ['   ├── {}'.format(sv.process(m))
              for m in r.methods if not m.internal or internal][:-1]
        ml += ['   └── {}'.format(sv.process(m))
               for m in r.methods if not m.internal or internal][-1:]

        exp = '⇒ {0.path} - {0.class_name}:\n{1}'.format(r, '\n'.join(ml))
        assert sv.process(r) == exp

    def test_route_verbose(self, internal):
        sv = inspect.StringVisitor(True, internal)
        r = inspect.inspect_routes(make_app())[0]

        ml = ['   ├── {}'.format(sv.process(m))
              for m in r.methods if not m.internal or internal][:-1]
        ml += ['   └── {}'.format(sv.process(m))
               for m in r.methods if not m.internal or internal][-1:]

        exp = '⇒ {0.path} - {0.class_name} ({0.source_info}):\n{1}'.format(r, '\n'.join(ml))
        assert sv.process(r) == exp

    def test_route_no_methods(self, internal):
        sv = inspect.StringVisitor(False, internal)
        r = inspect.inspect_routes(make_app())[0]
        r.methods.clear()
        exp = '⇒ {0.path} - {0.class_name}'.format(r)
        assert sv.process(r) == exp

    @pytest.mark.parametrize('verbose', (True, False))
    def test_static_route(self, verbose, internal):
        sv = inspect.StringVisitor(verbose, internal)
        sr = inspect.inspect_static_routes(make_app())
        no_file = sr[1]
        assert sv.process(no_file) == '↦ {0.prefix} {0.directory}'.format(no_file)
        with_file = sr[0]
        exp = '↦ {0.prefix} {0.directory} [{0.fallback_filename}]'.format(with_file)
        assert sv.process(with_file) == exp

    def test_sink(self, internal):
        sv = inspect.StringVisitor(False, internal)
        s = inspect.inspect_sinks(make_app())[0]

        assert sv.process(s) == '⇥ {0.prefix} {0.name}'.format(s)

    def test_sink_verbose(self, internal):
        sv = inspect.StringVisitor(True, internal)
        s = inspect.inspect_sinks(make_app())[0]

        assert sv.process(s) == '⇥ {0.prefix} {0.name} ({0.source_info})'.format(s)

    def test_error_handler(self, internal):
        sv = inspect.StringVisitor(False, internal)
        e = inspect.inspect_error_handlers(make_app())[0]

        assert sv.process(e) == '⇜ {0.error} {0.name}'.format(e)

    def test_error_handler_verbose(self, internal):
        sv = inspect.StringVisitor(True, internal)
        e = inspect.inspect_error_handlers(make_app())[0]

        assert sv.process(e) == '⇜ {0.error} {0.name} ({0.source_info})'.format(e)

    def test_middleware_method(self, internal):
        sv = inspect.StringVisitor(False, internal)
        mm = inspect.inspect_middleware(make_app()).middleware_classes[0].methods[0]

        assert sv.process(mm) == '{0.function_name}'.format(mm)

    def test_middleware_method_verbose(self, internal):
        sv = inspect.StringVisitor(True, internal)
        mm = inspect.inspect_middleware(make_app()).middleware_classes[0].methods[0]

        assert sv.process(mm) == '{0.function_name} ({0.source_info})'.format(mm)

    def test_middleware_class(self, internal):
        sv = inspect.StringVisitor(False, internal)
        mc = inspect.inspect_middleware(make_app()).middleware_classes[0]

        mml = ['   ├── {}'.format(sv.process(m)) for m in mc.methods][:-1]
        mml += ['   └── {}'.format(sv.process(m)) for m in mc.methods][-1:]

        exp = '↣ {0.name}:\n{1}'.format(mc, '\n'.join(mml))
        assert sv.process(mc) == exp

    def test_middleware_class_verbose(self, internal):
        sv = inspect.StringVisitor(True, internal)
        mc = inspect.inspect_middleware(make_app()).middleware_classes[0]

        mml = ['   ├── {}'.format(sv.process(m)) for m in mc.methods][:-1]
        mml += ['   └── {}'.format(sv.process(m)) for m in mc.methods][-1:]

        exp = '↣ {0.name} ({0.source_info}):\n{1}'.format(mc, '\n'.join(mml))
        assert sv.process(mc) == exp

    def test_middleware_class_no_methods(self, internal):
        sv = inspect.StringVisitor(False, internal)
        mc = inspect.inspect_middleware(make_app()).middleware_classes[0]
        mc.methods.clear()
        exp = '↣ {0.name}'.format(mc)
        assert sv.process(mc) == exp

    @pytest.mark.parametrize('verbose', (True, False))
    def test_middleware_tree_item(self, verbose, internal):
        sv = inspect.StringVisitor(verbose, internal)
        mt = inspect.inspect_middleware(make_app()).middleware_tree
        for r, s in ((mt.request[0], '→'), (mt.resource[0], '↣'), (mt.response[0], '↢')):
            assert sv.process(r) == '{0} {1.class_name}.{1.name}'.format(s, r)

    @pytest.mark.parametrize('verbose', (True, False))
    def test_middleware_tree(self, verbose, internal):
        sv = inspect.StringVisitor(verbose, internal)
        mt = inspect.inspect_middleware(make_app()).middleware_tree
        lines = []
        space = ''
        for r in mt.request:
            lines.append(space + sv.process(r))
            space += '  '
        lines.append('')
        for r in mt.resource:
            lines.append(space + sv.process(r))
            space += '  '
        lines.append('')
        lines.append(space + '  ├── Process route responder')
        lines.append('')
        for r in mt.response:
            space = space[:-2]
            lines.append(space + sv.process(r))

        assert sv.process(mt) == '\n'.join(lines)

    def test_middleware_tree_response_only(self, internal):
        sv = inspect.StringVisitor(False, internal)
        mt = inspect.inspect_middleware(make_app()).middleware_tree
        mt.request.clear()
        mt.resource.clear()
        lines = []
        space = '  ' * len(mt.response)
        lines.append('')
        lines.append(space + '  ├── Process route responder')
        lines.append('')
        for r in mt.response:
            space = space[:-2]
            lines.append(space + sv.process(r))

        assert sv.process(mt) == '\n'.join(lines)

    def test_middleware_tree_no_response(self, internal):
        sv = inspect.StringVisitor(False, internal)
        mt = inspect.inspect_middleware(make_app()).middleware_tree
        mt.response.clear()
        lines = []
        space = ''
        for r in mt.request:
            lines.append(space + sv.process(r))
            space += '  '
        lines.append('')
        for r in mt.resource:
            lines.append(space + sv.process(r))
            space += '  '
        lines.append('')
        lines.append(space + '  ├── Process route responder')

        assert sv.process(mt) == '\n'.join(lines)

    def test_middleware_tree_no_resource(self, internal):
        sv = inspect.StringVisitor(False, internal)
        mt = inspect.inspect_middleware(make_app()).middleware_tree
        mt.resource.clear()
        lines = []
        space = '  '
        for r in mt.request:
            lines.append(space + sv.process(r))
            space += '  '
        lines.append('')
        lines.append(space + '  ├── Process route responder')
        lines.append('')
        for r in mt.response:
            space = space[:-2]
            lines.append(space + sv.process(r))

        assert sv.process(mt) == '\n'.join(lines)

    def test_middleware(self, internal):
        sv = inspect.StringVisitor(False, internal)
        m = inspect.inspect_middleware(make_app())

        assert sv.process(m) == sv.process(m.middleware_tree)

    def test_middleware_verbose(self, internal):
        sv = inspect.StringVisitor(True, internal)
        m = inspect.inspect_middleware(make_app())

        mt = sv.process(m.middleware_tree)
        sv.indent += 4
        mc = '\n'.join(sv.process(cls) for cls in m.middleware_classes)
        exp = '{}\n- Middleware classes:\n{}'.format(mt, mc)
        assert inspect.StringVisitor(True).process(m) == exp

    def make(self, sv, app, v, i, r=True, m=True, sr=True, s=True, e=True):
        text = 'Falcon App (WSGI)'
        sv.indent = 4
        if r:
            text += '\n• Routes:\n{}'.format('\n'.join(sv.process(r) for r in app.routes))
        if m:
            mt = sv.process(app.middleware)
            text += '\n• Middleware ({}):\n{}'.format(app.middleware.independent_text, mt)
        if sr:
            sr = '\n'.join(sv.process(sr) for sr in app.static_routes)
            text += '\n• Static routes:\n{}'.format(sr)
        if s:
            text += '\n• Sinks:\n{}'.format('\n'.join(sv.process(s) for s in app.sinks))
        if e:
            err = '\n'.join(sv.process(e) for e in app.error_handlers if not e.internal or i)
            text += '\n• Error handlers:\n{}'.format(err)
        return text

    @pytest.mark.parametrize('verbose', (True, False))
    def test_app(self, verbose, internal):
        sv = inspect.StringVisitor(verbose, internal)
        app = inspect.inspect_app(make_app())

        assert inspect.StringVisitor(verbose, internal).process(app) == self.make(
            sv, app, verbose, internal)

    @pytest.mark.parametrize('verbose', (True, False))
    def test_app_no_routes(self, verbose, internal):
        sv = inspect.StringVisitor(verbose, internal)
        app = inspect.inspect_app(make_app())
        app.routes.clear()
        assert inspect.StringVisitor(verbose, internal).process(app) == self.make(
            sv, app, verbose, internal, r=False)

    @pytest.mark.parametrize('verbose', (True, False))
    def test_app_no_middleware(self, verbose, internal):
        sv = inspect.StringVisitor(verbose, internal)
        app = inspect.inspect_app(make_app())
        app.middleware.middleware_classes.clear()
        app.middleware.middleware_tree.request.clear()
        app.middleware.middleware_tree.resource.clear()
        app.middleware.middleware_tree.response.clear()
        assert inspect.StringVisitor(verbose, internal).process(app) == self.make(
            sv, app, verbose, internal, m=False)

    @pytest.mark.parametrize('verbose', (True, False))
    def test_app_static_routes(self, verbose, internal):
        sv = inspect.StringVisitor(verbose, internal)
        app = inspect.inspect_app(make_app())
        app.static_routes.clear()
        assert inspect.StringVisitor(verbose, internal).process(app) == self.make(
            sv, app, verbose, internal, sr=False)

    @pytest.mark.parametrize('verbose', (True, False))
    def test_app_no_sink(self, verbose, internal):
        sv = inspect.StringVisitor(verbose, internal)
        app = inspect.inspect_app(make_app())
        app.sinks.clear()
        assert inspect.StringVisitor(verbose, internal).process(app) == self.make(
            sv, app, verbose, internal, s=False)

    @pytest.mark.parametrize('verbose', (True, False))
    def test_app_no_errors(self, verbose, internal):
        sv = inspect.StringVisitor(verbose, internal)
        app = inspect.inspect_app(make_app())
        app.error_handlers.clear()
        assert inspect.StringVisitor(verbose, internal).process(app) == self.make(
            sv, app, verbose, internal, e=False)

    def test_app_name(self, internal):
        sv = inspect.StringVisitor(False, internal, name='foo')
        app = inspect.inspect_app(make_app())

        s = sv.process(app).splitlines()[0]
        assert s == 'foo (WSGI)'
        assert app.to_string(name='bar').splitlines()[0] == 'bar (WSGI)'


def test_is_internal():
    assert inspect._is_internal(1) is False
    assert inspect._is_internal(dict) is False
    assert inspect._is_internal(inspect) is True
