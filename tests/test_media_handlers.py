from functools import partial
import io
import json
import platform
import sys

import mujson
import pytest
import ujson

import falcon
from falcon import ASGI_SUPPORTED, media, testing

from _util import create_app  # NOQA


orjson = None
rapidjson = None
if sys.version_info >= (3, 5):
    import rapidjson  # type: ignore

    if platform.python_implementation() == 'CPython':
        try:
            import orjson  # type: ignore
        except ImportError:
            pass


COMMON_SERIALIZATION_PARAM_LIST = [
    # Default json.dumps, with only ascii
    (None, {'test': 'value'}, b'{"test":"value"}'),
    (partial(mujson.dumps, ensure_ascii=True), {'test': 'value'}, b'{"test":"value"}'),
    (ujson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    (partial(lambda media, **kwargs: json.dumps([media, kwargs]),
     ensure_ascii=True),
     {'test': 'value'},
     b'[{"test":"value"},{"ensure_ascii":true}]'),
]

COMMON_DESERIALIZATION_PARAM_LIST = [
    (None, b'[1, 2]', [1, 2]),
    (partial(json.loads,
             object_hook=lambda data: {k: v.upper() for k, v in data.items()}),
     b'{"key": "value"}',
     {'key': 'VALUE'}),

    (mujson.loads, b'{"test": "value"}', {'test': 'value'}),
    (ujson.loads, b'{"test": "value"}', {'test': 'value'}),
]

YEN = b'\xc2\xa5'

if orjson:
    SERIALIZATION_PARAM_LIST = COMMON_SERIALIZATION_PARAM_LIST + [
        # Default json.dumps, with non-ascii characters
        (None, {'yen': YEN.decode()}, b'{"yen":"' + YEN + b'"}'),

        # Extra Python 3 json libraries
        (rapidjson.dumps, {'test': 'value'}, b'{"test":"value"}'),
        (orjson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    ]

    DESERIALIZATION_PARAM_LIST = COMMON_DESERIALIZATION_PARAM_LIST + [
        (rapidjson.loads, b'{"test": "value"}', {'test': 'value'}),
        (orjson.loads, b'{"test": "value"}', {'test': 'value'}),
    ]
elif rapidjson:
    SERIALIZATION_PARAM_LIST = COMMON_SERIALIZATION_PARAM_LIST + [
        # Default json.dumps, with non-ascii characters
        (None, {'yen': YEN.decode()}, b'{"yen":"' + YEN + b'"}'),

        # Extra Python 3 json libraries
        (rapidjson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    ]

    DESERIALIZATION_PARAM_LIST = COMMON_DESERIALIZATION_PARAM_LIST + [
        (rapidjson.loads, b'{"test": "value"}', {'test': 'value'}),
    ]
else:
    SERIALIZATION_PARAM_LIST = COMMON_SERIALIZATION_PARAM_LIST + [
        # Default json.dumps, with non-ascii characters
        (None, {'yen': YEN.decode('utf-8')}, b'{"yen":"' + YEN + b'"}'),
    ]
    DESERIALIZATION_PARAM_LIST = COMMON_DESERIALIZATION_PARAM_LIST


@pytest.mark.parametrize('func, body, expected', SERIALIZATION_PARAM_LIST)
def test_serialization(asgi, func, body, expected):
    handler = media.JSONHandler(dumps=func)

    args = (body, b'application/javacript')

    if asgi:
        result = falcon.invoke_coroutine_sync(handler.serialize_async, *args)
    else:
        result = handler.serialize(*args)

    # NOTE(nZac) PyPy and CPython render the final string differently. One
    # includes spaces and the other doesn't. This replace will normalize that.
    assert result.replace(b' ', b'') == expected  # noqa


@pytest.mark.parametrize('func, body, expected', DESERIALIZATION_PARAM_LIST)
def test_deserialization(asgi, func, body, expected):
    handler = media.JSONHandler(loads=func)

    args = ['application/javacript', len(body)]

    if asgi:
        if not ASGI_SUPPORTED:
            pytest.skip('ASGI requires Python 3.6+')

        from falcon.asgi.stream import BoundedStream

        s = BoundedStream(testing.ASGIRequestEventEmitter(body))
        args.insert(0, s)

        result = falcon.invoke_coroutine_sync(handler.deserialize_async, *args)
    else:
        args.insert(0, io.BytesIO(body))
        result = handler.deserialize(*args)

    assert result == expected


def test_deserialization_raises(asgi):
    app = create_app(asgi)

    class SuchException(Exception):
        pass

    class FaultyHandler(media.BaseHandler):
        def deserialize(self, stream, content_type, content_length):
            raise SuchException('Wow such error.')

        def deserialize_async(self, stream, content_type, content_length):
            raise SuchException('Wow such error.')

        def serialize(self, media, content_type):
            raise SuchException('Wow such error.')

    handlers = media.Handlers({'application/json': FaultyHandler()})
    app.req_options.media_handlers = handlers
    app.resp_options.media_handlers = handlers

    class Resource:
        def on_get(self, req, resp):
            resp.media = {}

        def on_post(self, req, resp):
            req.media

    class ResourceAsync:
        async def on_get(self, req, resp):
            resp.media = {}

        async def on_post(self, req, resp):
            # NOTE(kgriffs): In this one case we use the property
            #   instead of get_media(), in order to test that the
            #   alias works as expected.
            await req.media

    app.add_route('/', ResourceAsync() if asgi else Resource())

    # NOTE(kgriffs): Now that we install a default handler for
    #   Exception, we have to clear them to test the path we want
    #   to trigger.
    # TODO(kgriffs): Since we always add a default error handler
    #   for Exception, should we take out the checks in the WSGI/ASGI
    #   callable and just always assume it will be handled? If so,
    #   it makes testing that the right exception is propagated harder;
    #   I suppose we'll have to look at what is logged.
    app._error_handlers.clear()

    with pytest.raises(SuchException):
        testing.simulate_get(app, '/')

    with pytest.raises(SuchException):
        testing.simulate_post(app, '/', json={})


def test_sync_methods_not_overridden(asgi):
    app = create_app(asgi)

    class FaultyHandler(media.BaseHandler):
        pass

    handlers = media.Handlers({'application/json': FaultyHandler()})
    app.req_options.media_handlers = handlers
    app.resp_options.media_handlers = handlers

    class Resource:
        def on_get(self, req, resp):
            resp.media = {}

        def on_post(self, req, resp):
            req.media

    class ResourceAsync:
        async def on_get(self, req, resp):
            resp.media = {}

        async def on_post(self, req, resp):
            await req.get_media()

    app.add_route('/', ResourceAsync() if asgi else Resource())

    result = testing.simulate_get(app, '/')
    assert result.status_code == 500

    result = testing.simulate_post(app, '/', json={})
    assert result.status_code == 500


def test_async_methods_not_overridden():
    app = create_app(asgi=True)

    class SimpleHandler(media.BaseHandler):
        def serialize(self, media, content_type):
            return json.dumps(media).encode()

        def deserialize(self, stream, content_type, content_length):
            return json.load(stream)

    handlers = media.Handlers({'application/json': SimpleHandler()})
    app.req_options.media_handlers = handlers
    app.resp_options.media_handlers = handlers

    class ResourceAsync:
        async def on_post(self, req, resp):
            resp.media = await req.get_media()

    app.add_route('/', ResourceAsync())

    doc = {'event': 'serialized'}
    result = testing.simulate_post(app, '/', json=doc)
    assert result.status_code == 200
    assert result.json == doc


def test_async_handler_returning_none():
    app = create_app(asgi=True)

    class SimpleHandler(media.BaseHandler):
        def serialize(self, media, content_type):
            return json.dumps(media).encode()

        def deserialize(self, stream, content_type, content_length):
            return None

    handlers = media.Handlers({'application/json': SimpleHandler()})
    app.req_options.media_handlers = handlers
    app.resp_options.media_handlers = handlers

    class ResourceAsync:
        async def on_post(self, req, resp):
            resp.media = [await req.get_media()]

    app.add_route('/', ResourceAsync())

    doc = {'event': 'serialized'}
    result = testing.simulate_post(app, '/', json=doc)
    assert result.status_code == 200
    assert result.json == [None]
