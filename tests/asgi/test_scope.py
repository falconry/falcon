import asyncio

import pytest

import falcon
from falcon import testing
from falcon.asgi import App
from falcon.errors import UnsupportedError
from falcon.errors import UnsupportedScopeError


class CustomCookies:
    def items(self):
        return [('foo', 'bar')]


def test_missing_asgi_version():
    scope = testing.create_scope()
    del scope['asgi']

    resource = _call_with_scope(scope)

    # NOTE(kgriffs): According to the ASGI spec, the version should
    #   default to "2.0".
    assert resource.captured_req.scope['asgi']['version'] == '2.0'


@pytest.mark.parametrize('http_version', ['0.9', '1.9', '4.0', '1337'])
def test_unsupported_http_version(http_version):
    scope = testing.create_scope()
    scope['http_version'] = http_version

    with pytest.raises(UnsupportedError):
        _call_with_scope(scope)


@pytest.mark.parametrize(
    'version, supported',
    [
        ('3.0', True),
        ('3.1', True),
        ('3.10', True),
        ('30.0', False),
        ('31.0', False),
        ('4.0', False),
        ('4.1', False),
        ('4.10', False),
        ('40.0', False),
        ('41.0', False),
        ('2.0', False),
        ('2.1', False),
        ('2.10', False),
        (None, False),
    ],
)
def test_supported_asgi_version(version, supported):
    scope = {
        'type': 'lifespan',
        'asgi': {'spec_version': '2.0', 'version': version},
    }
    if version is None:
        del scope['asgi']['version']

    app = App()

    resource = testing.SimpleTestResourceAsync()
    app.add_route('/', resource)

    shutting_down = asyncio.Condition()
    req_event_emitter = testing.ASGILifespanEventEmitter(shutting_down)
    resp_event_collector = testing.ASGIResponseEventCollector()

    async def task():
        coro = asyncio.create_task(app(scope, req_event_emitter, resp_event_collector))

        # NOTE(vytas): Yield to the lifespan task above.
        await asyncio.sleep(0)

        assert len(resp_event_collector.events) == 1
        event = resp_event_collector.events[0]
        if supported:
            assert event['type'] == 'lifespan.startup.complete'
        else:
            assert event['type'] == 'lifespan.startup.failed'
            assert event['message'].startswith('Falcon requires ASGI version 3.x')

        async with shutting_down:
            shutting_down.notify()

        await coro

    falcon.async_to_sync(task)


@pytest.mark.parametrize('scope_type', ['tubes', 'http3', 'htt'])
def test_unsupported_scope_type(scope_type):
    scope = testing.create_scope()
    scope['type'] = scope_type
    with pytest.raises(UnsupportedScopeError):
        _call_with_scope(scope)


@pytest.mark.parametrize(
    'spec_version, supported',
    [
        ('0.0', False),
        ('1.0', False),
        ('11.0', False),
        ('2.0', True),
        ('2.1', True),
        ('2.10', True),
        ('20.0', False),
        ('22.0', False),
        ('3.0', False),
        ('3.1', False),
        ('30.0', False),
    ],
)
def test_supported_http_spec(spec_version, supported):
    scope = testing.create_scope()
    scope['asgi']['spec_version'] = spec_version

    if supported:
        _call_with_scope(scope)
    else:
        with pytest.raises(UnsupportedScopeError):
            _call_with_scope(scope)


def test_lifespan_scope_default_version():
    app = App()

    resource = testing.SimpleTestResourceAsync()

    app.add_route('/', resource)

    shutting_down = asyncio.Condition()
    req_event_emitter = testing.ASGILifespanEventEmitter(shutting_down)
    resp_event_collector = testing.ASGIResponseEventCollector()

    scope = {'type': 'lifespan'}

    async def t():
        t = asyncio.create_task(app(scope, req_event_emitter, resp_event_collector))

        # NOTE(kgriffs): Yield to the lifespan task above
        await asyncio.sleep(0.001)

        async with shutting_down:
            shutting_down.notify()

        await t

    falcon.async_to_sync(t)

    assert not resource.called


@pytest.mark.parametrize(
    'spec_version, supported',
    [
        ('0.0', False),
        ('1.0', True),
        ('1.1', True),
        ('1.10', True),
        ('2.0', True),
        ('2.1', True),
        ('2.10', True),
        ('3.0', False),
        ('4.0', False),
        ('11.0', False),
        ('22.0', False),
    ],
)
def test_lifespan_scope_version(spec_version, supported):
    app = App()

    shutting_down = asyncio.Condition()
    req_event_emitter = testing.ASGILifespanEventEmitter(shutting_down)
    resp_event_collector = testing.ASGIResponseEventCollector()

    scope = {
        'type': 'lifespan',
        'asgi': {'spec_version': spec_version, 'version': '3.0'},
    }

    if not supported:
        with pytest.raises(UnsupportedScopeError):
            falcon.async_to_sync(
                app.__call__, scope, req_event_emitter, resp_event_collector
            )

        return

    async def t():
        t = asyncio.create_task(app(scope, req_event_emitter, resp_event_collector))

        # NOTE(kgriffs): Yield to the lifespan task above
        await asyncio.sleep(0.001)

        async with shutting_down:
            shutting_down.notify()

        await t

    falcon.async_to_sync(t)


def test_query_string_values():
    with pytest.raises(ValueError):
        testing.create_scope(query_string='?catsup=y')

    with pytest.raises(ValueError):
        testing.create_scope(query_string='?')

    for qs in ('', None):
        scope = testing.create_scope(query_string=qs)
        assert scope['query_string'] == b''

        resource = _call_with_scope(scope)
        assert resource.captured_req.query_string == ''

    qs = 'a=1&b=2&c=%3E%20%3C'
    scope = testing.create_scope(query_string=qs)
    assert scope['query_string'] == qs.encode()

    resource = _call_with_scope(scope)
    assert resource.captured_req.query_string == qs


@pytest.mark.parametrize(
    'scheme, valid',
    [
        ('http', True),
        ('https', True),
        ('htt', False),
        ('http:', False),
        ('https:', False),
        ('ftp', False),
        ('gopher', False),
    ],
)
def test_scheme(scheme, valid):
    if valid:
        testing.create_scope(scheme=scheme)
    else:
        with pytest.raises(ValueError):
            testing.create_scope(scheme=scheme)


@pytest.mark.parametrize('cookies', [{'foo': 'bar', 'baz': 'foo'}, CustomCookies()])
def test_cookies(cookies):
    scope = testing.create_scope(cookies=cookies)
    assert any(header == b'cookie' for header, _ in scope['headers'])


def test_cookies_options_meathod():
    scope = testing.create_scope(method='OPTIONS', cookies={'foo': 'bar'})
    assert not any(header == b'cookie' for header, _ in scope['headers'])


def _call_with_scope(scope):
    app = App()

    resource = testing.SimpleTestResourceAsync()

    app.add_route('/', resource)

    req_event_emitter = testing.ASGIRequestEventEmitter()
    resp_event_collector = testing.ASGIResponseEventCollector()

    falcon.async_to_sync(app.__call__, scope, req_event_emitter, resp_event_collector)

    assert resource.called
    return resource
