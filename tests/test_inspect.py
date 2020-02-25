import os

import _inspect_fixture as i_f

from falcon import App, inspect
from falcon.asgi import App as AsyncApp


def make_app():
    app = App(cors_enable=True)
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
    app = AsyncApp(cors_enable=True)
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
        ai = inspect.inspect_app(AsyncApp() if asgi else App())

        assert ai.routes == []
        assert ai.middleware.middleware_tree.request == []
        assert ai.middleware.middleware_tree.resource == []
        assert ai.middleware.middleware_tree.response == []
        assert ai.middleware.middleware_classes == []
        assert ai.middleware.independent is True
        assert ai.static_routes == []
        assert ai.sinks == []
        assert len(ai.error_handlers) == 3
        assert ai.asgi is asgi

    def test_dependent_middlewares(self, asgi):
        app = AsyncApp(independent_middleware=False) if asgi else App(independent_middleware=False)
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
        assert len(ai.error_handlers) == 4
        assert ai.asgi is asgi

    def test_routes(self, asgi):
        routes = inspect.inspect_routes(make_app_async() if asgi else make_app())

        def test(r, p, cn, ml, fnt):
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

        test(routes[0], '/foo', 'MyResponder', ['GET', 'POST', 'DELETE'], 'on_{}')
        test(routes[1], '/foo/{id}', 'MyResponder', ['GET', 'PUT', 'DELETE'], 'on_{}_id')
        test(routes[2], '/bar', 'OtherResponder', ['POST'], 'on_{}_id')

    def test_static_routes(self, asgi):
        routes = inspect.inspect_static_routes(make_app_async() if asgi else make_app())

        assert all(isinstance(sr, inspect.StaticRouteInfo) for sr in routes)
        assert routes[-1].prefix == '/fal/'
        assert routes[-1].directory == os.path.abspath('falcon')
        assert routes[-1].fallback_filename is None
        assert routes[-2].prefix == '/tes/'
        assert routes[-2].directory == os.path.abspath('tests')
        assert routes[-2].fallback_filename.endswith('conftest.py')

    def test_sync(self, asgi):
        sinks = inspect.inspect_sinks(make_app_async() if asgi else make_app())

        assert all(isinstance(s, inspect.SinkInfo) for s in sinks)
        assert sinks[-1].prefix == '/sink_fn'
        assert sinks[-1].name == 'sinkFn'
        assert '_inspect_fixture.py' in sinks[-1].source_info
        assert sinks[-2].prefix == '/sink_cls'
        assert sinks[-2].name == 'SinkClass'
        assert '_inspect_fixture.py' in sinks[-2].source_info

    def test_error_handler(self, asgi):
        errors = inspect.inspect_error_handlers(make_app_async() if asgi else make_app())

        assert all(isinstance(e, inspect.ErrorHandlerInfo) for e in errors)
        assert errors[-1].error == 'RuntimeError'
        assert errors[-1].name == 'my_error_handler_async' if asgi else 'my_error_handler'
        assert '_inspect_fixture.py' in errors[-1].source_info
        assert errors[-1].internal is False
        for eh in errors[:-1]:
            assert eh.internal
            assert eh.error in ('Exception', 'HTTPStatus', 'HTTPError')

    def test_middleware(self, asgi):
        mi = inspect.inspect_middlewares(make_app_async() if asgi else make_app())

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
        mi = inspect.inspect_middlewares(make_app_async() if asgi else make_app())

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
