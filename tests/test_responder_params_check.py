import inspect
import warnings

import pytest

import falcon
from falcon.routing import CompiledRouter
from falcon.routing import ResponderParamsWarning
from falcon.routing.compiled import UnacceptableRouteError


@pytest.fixture
def router():
    return CompiledRouter()


def _add_route_warnings(router_or_app, uri_template, resource, **kwargs):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        router_or_app.add_route(uri_template, resource, **kwargs)

    return [
        str(warning.message)
        for warning in caught
        if issubclass(warning.category, ResponderParamsWarning)
    ]


def _create_mismatched_resource(asgi):
    if asgi:

        class AsyncItemResource:
            async def on_get(self, req, resp, itemid):
                pass

            async def on_get_item(self, req, resp, item_id):
                pass

        return AsyncItemResource()

    class ItemResource:
        def on_get(self, req, resp, itemid):
            pass

        def on_get_item(self, req, resp, item_id):
            pass

    return ItemResource()


class CallableResponder:
    def __call__(self, req, resp):
        pass

    def __repr__(self):
        return 'CallableResponder()'


class UninspectableResponder(CallableResponder):
    # NOTE: inspect.signature() raises TypeError for such objects.
    __signature__ = 'not a signature'


class ResourceWithAliases:
    def on_get(self, req, resp):
        pass

    on_head = on_get


class ResourceWithHook:
    @falcon.before(lambda req, resp, resource, params: None)
    def on_get(self, req, resp, item_id):
        pass

    @falcon.before(lambda req, resp, resource, params: None)
    def on_put(self, req, resp):
        pass


def _method(params):
    namespace = {}
    exec(f'def on_get(self, req, resp{params}):\n    pass', namespace)
    on_get = namespace['on_get']
    on_get.__qualname__ = 'Resource.on_get'
    return on_get


def _expected_message(responder, fields, uri_template):
    return (
        f'Responder {responder.__qualname__}() does not accept the field(s) '
        f'{fields} of the URI template "{uri_template}".'
    )


@pytest.mark.parametrize(
    'params,unaccepted',
    [
        (', item_id, part_id', ''),
        (', *, item_id, part_id', ''),
        (', item_id, part_id=None', ''),
        (', item_id, part_id, extra', ''),
        (', item_id, part_id, extra=None', ''),
        (', **kwargs', ''),
        (', item_id, **kwargs', ''),
        (', item_id, part_id, extra, **kwargs', ''),
        ('', '"item_id", "part_id"'),
        (', item_id', '"part_id"'),
        (', itemid, part_id', '"item_id"'),
        (', item_id, partid=None', '"part_id"'),
        (', *args', '"item_id", "part_id"'),
        (', *args, item_id', '"part_id"'),
        (', item_id, part_id, /', '"item_id", "part_id"'),
        (', item_id, /, part_id', '"item_id"'),
    ],
)
def test_responder_params(router, params, unaccepted):
    resource = type('Resource', (), {'on_get': _method(params)})()

    messages = _add_route_warnings(router, '/items/{item_id}/{part_id}', resource)

    if unaccepted:
        assert messages == [
            f'Responder Resource.on_get() does not accept the field(s) '
            f'{unaccepted} of the URI template "/items/{{item_id}}/{{part_id}}".'
        ]
    else:
        assert messages == []


@pytest.mark.parametrize(
    'params',
    [
        'req, resp, item_id',
        '*args, item_id',
        'req, *args, item_id',
        '*, item_id, **kwargs',
    ],
)
def test_responder_params_req_resp(router, params):
    namespace = {}
    exec(f'def on_get(self, {params}):\n    pass', namespace)
    resource = type('Resource', (), {'on_get': namespace['on_get']})()

    assert _add_route_warnings(router, '/items/{item_id}', resource) == []


def test_template_without_fields(router):
    resource = type('Resource', (), {'on_get': _method(', item_id')})()

    assert _add_route_warnings(router, '/items', resource) == []
    assert _add_route_warnings(router, '/items/all', resource) == []


def test_responder_checked_once(router):
    messages = _add_route_warnings(router, '/items/{item_id}', ResourceWithAliases())

    assert messages == [
        'Responder ResourceWithAliases.on_get() does not accept the field(s) '
        '"item_id" of the URI template "/items/{item_id}".'
    ]


def test_hooks(router):
    messages = _add_route_warnings(router, '/items/{item_id}', ResourceWithHook())

    assert messages == [
        'Responder ResourceWithHook.on_put() does not accept the field(s) '
        '"item_id" of the URI template "/items/{item_id}".'
    ]


def test_responder_without_qualname(router):
    resource = type('Resource', (), {'on_get': CallableResponder()})()

    messages = _add_route_warnings(router, '/items/{item_id}', resource)

    assert messages == [
        'Responder CallableResponder()() does not accept the field(s) '
        '"item_id" of the URI template "/items/{item_id}".'
    ]


def test_uninspectable_responder(router):
    responder = UninspectableResponder()
    with pytest.raises(TypeError):
        inspect.signature(responder)

    resource = type('Resource', (), {'on_get': responder})()

    assert _add_route_warnings(router, '/items/{item_id}', resource) == []


def test_default_responders_not_checked(asgi, util):
    class AsyncResource:
        async def on_get(self, req, resp, item_id):
            pass

    class Resource:
        def on_get(self, req, resp, item_id):
            pass

    app = util.create_app(asgi)
    resource = AsyncResource() if asgi else Resource()

    # NOTE: The default responders (e.g., OPTIONS, 405) accept **kwargs; this
    #   test makes sure that only the responders defined on the resource are
    #   checked, even if their implementation changes.
    assert _add_route_warnings(app, '/items/{item_id}', resource) == []


@pytest.mark.parametrize('mode', ['warn', 'error', 'off'])
def test_modes(asgi, util, mode):
    app = util.create_app(asgi)
    if mode != 'warn':
        app.router_options.check_responder_params = mode
    resource = _create_mismatched_resource(asgi)
    expected = _expected_message(resource.on_get, '"item_id"', '/items/{item_id}')

    if mode == 'error':
        with pytest.raises(UnacceptableRouteError) as exc_info:
            app.add_route('/items/{item_id}', resource)

        assert str(exc_info.value) == expected
        assert app._router.find('/items/42') is None
    elif mode == 'warn':
        assert _add_route_warnings(app, '/items/{item_id}', resource) == [expected]
        assert app._router.find('/items/42') is not None
    else:
        assert _add_route_warnings(app, '/items/{item_id}', resource) == []
        assert app._router.find('/items/42') is not None


def test_default_mode(router):
    assert router.options.check_responder_params == 'warn'


@pytest.mark.parametrize('value', ['', 'Warn', 'ignore', None, True, 1])
def test_invalid_mode(router, value):
    with pytest.raises(ValueError, match='check_responder_params must be one of'):
        router.options.check_responder_params = value

    assert router.options.check_responder_params == 'warn'


def test_warning_category():
    assert issubclass(ResponderParamsWarning, UserWarning)
    assert falcon.routing.ResponderParamsWarning is ResponderParamsWarning


def test_warning_stacklevel(asgi, util):
    app = util.create_app(asgi)
    resource = _create_mismatched_resource(asgi)

    with pytest.warns(ResponderParamsWarning) as record:
        app.add_route('/items/{item_id}', resource)

    assert len(record) == 1
    assert record[0].filename == __file__


def test_warning_stacklevel_router(router):
    resource = _create_mismatched_resource(False)

    with pytest.warns(ResponderParamsWarning) as record:
        router.add_route('/items/{item_id}', resource)

    assert len(record) == 1
    assert record[0].filename == __file__


def test_warning_filter(asgi, util):
    app = util.create_app(asgi)
    resource = _create_mismatched_resource(asgi)

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        warnings.simplefilter('ignore', ResponderParamsWarning)
        app.add_route('/items/{item_id}', resource)


def test_suffix(asgi, util):
    app = util.create_app(asgi)
    resource = _create_mismatched_resource(asgi)

    # NOTE: on_get() does not accept item_id, but it is not mapped to this
    #   route, since on_get_item() is used instead.
    messages = _add_route_warnings(app, '/items/{item_id}', resource, suffix='item')
    assert messages == []

    messages = _add_route_warnings(app, '/things/{thing_id}', resource, suffix='item')
    assert messages == [
        _expected_message(resource.on_get_item, '"thing_id"', '/things/{thing_id}')
    ]


@pytest.mark.parametrize('suffix', [None, 'item'])
def test_default_to_on_request(asgi, util, suffix):
    if asgi:

        class AsyncResource:
            async def on_get(self, req, resp, item_id):
                pass

            async def on_request(self, req, resp):
                pass

            async def on_get_item(self, req, resp, item_id):
                pass

            async def on_request_item(self, req, resp):
                pass

        resource = AsyncResource()
    else:

        class Resource:
            def on_get(self, req, resp, item_id):
                pass

            def on_request(self, req, resp):
                pass

            def on_get_item(self, req, resp, item_id):
                pass

            def on_request_item(self, req, resp):
                pass

        resource = Resource()

    app = util.create_app(asgi)
    assert _add_route_warnings(app, '/items/{item_id}', resource, suffix=suffix) == []

    app = util.create_app(asgi)
    app.router_options.default_to_on_request = True
    responder = resource.on_request_item if suffix else resource.on_request
    messages = _add_route_warnings(app, '/items/{item_id}', resource, suffix=suffix)
    assert messages == [_expected_message(responder, '"item_id"', '/items/{item_id}')]


def test_default_to_on_request_missing(router):
    router.options.default_to_on_request = True
    resource = type('Resource', (), {'on_get': _method(', item_id')})()

    assert _add_route_warnings(router, '/items/{item_id}', resource) == []


def test_on_websocket(util):
    class Resource:
        async def on_get(self, req, resp, item_id):
            pass

        async def on_websocket(self, req, ws):
            pass

    class ResourceWithParams:
        async def on_websocket(self, req, ws, item_id):
            pass

    app = util.create_app(True)

    messages = _add_route_warnings(app, '/items/{item_id}', Resource())
    assert messages == [
        'Responder test_on_websocket.<locals>.Resource.on_websocket() does not '
        'accept the field(s) "item_id" of the URI template "/items/{item_id}".'
    ]

    messages = _add_route_warnings(app, '/ws/{item_id}', ResourceWithParams())
    assert messages == []
