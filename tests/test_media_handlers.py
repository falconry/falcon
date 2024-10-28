from functools import partial
import io
import json
import platform

import pytest

import falcon
from falcon import media
from falcon import testing
from falcon.asgi.stream import BoundedStream
from falcon.constants import MEDIA_JSON
from falcon.constants import MEDIA_YAML

mujson = None
orjson = None
rapidjson = None
ujson = None

try:
    import mujson  # type: ignore
except ImportError:
    pass

try:
    import rapidjson  # type: ignore
except ImportError:
    pass

try:
    import ujson  # type: ignore
except ImportError:
    pass

if platform.python_implementation() == 'CPython':
    try:
        import orjson  # type: ignore
    except ImportError:
        pass

YEN = b'\xc2\xa5'

SERIALIZATION_PARAM_LIST = [
    # Default json.dumps, with only ascii
    (None, {'test': 'value'}, b'{"test":"value"}'),
    (
        partial(lambda media, **kwargs: json.dumps([media, kwargs]), ensure_ascii=True),
        {'test': 'value'},
        b'[{"test":"value"},{"ensure_ascii":true}]',
    ),
    # Default json.dumps, with non-ascii characters
    (None, {'yen': YEN.decode()}, b'{"yen":"' + YEN + b'"}'),
]

DESERIALIZATION_PARAM_LIST = [
    (None, b'[1, 2]', [1, 2]),
    (
        partial(
            json.loads, object_hook=lambda data: {k: v.upper() for k, v in data.items()}
        ),
        b'{"key": "value"}',
        {'key': 'VALUE'},
    ),
]

ALL_JSON_IMPL = [(json.dumps, json.loads)]
ALL_JSON_IMPL_IDS = ['stdlib']


if mujson:
    SERIALIZATION_PARAM_LIST += [
        (
            partial(mujson.dumps, ensure_ascii=True),
            {'test': 'value'},
            b'{"test":"value"}',
        ),
    ]
    DESERIALIZATION_PARAM_LIST += [
        (mujson.loads, b'{"test": "value"}', {'test': 'value'}),
    ]
    ALL_JSON_IMPL += [(partial(mujson.dumps, ensure_ascii=True), mujson.loads)]
    ALL_JSON_IMPL_IDS += ['mujson']

if orjson:
    SERIALIZATION_PARAM_LIST += [
        (orjson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    ]
    DESERIALIZATION_PARAM_LIST += [
        (orjson.loads, b'{"test": "value"}', {'test': 'value'}),
    ]
    ALL_JSON_IMPL += [(orjson.dumps, orjson.loads)]
    ALL_JSON_IMPL_IDS += ['orjson']

if rapidjson:
    SERIALIZATION_PARAM_LIST += [
        (rapidjson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    ]
    DESERIALIZATION_PARAM_LIST += [
        (rapidjson.loads, b'{"test": "value"}', {'test': 'value'}),
    ]
    ALL_JSON_IMPL += [(rapidjson.dumps, rapidjson.loads)]
    ALL_JSON_IMPL_IDS += ['rapidjson']

if ujson:
    SERIALIZATION_PARAM_LIST += [
        (ujson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    ]
    DESERIALIZATION_PARAM_LIST += [
        (ujson.loads, b'{"test": "value"}', {'test': 'value'}),
    ]
    ALL_JSON_IMPL += [(ujson.dumps, ujson.loads)]
    ALL_JSON_IMPL_IDS += ['ujson']


@pytest.mark.parametrize(
    'library, name',
    [
        (mujson, 'mujson'),
        (orjson, 'orjson'),
        (rapidjson, 'rapidjson'),
        (ujson, 'ujson'),
    ],
    ids=['mujson', 'orjson', 'rapidjson', 'ujson'],
)
def test_check_json_library(library, name):
    # NOTE(vytas): A synthetic test just to visualize which JSON libraries
    #   are absent and skipped.
    if library is None:
        pytest.skip(f'{name} is not installed')
    assert hasattr(library, 'dumps')
    assert hasattr(library, 'loads')


@pytest.mark.parametrize('func, body, expected', SERIALIZATION_PARAM_LIST)
def test_serialization(asgi, func, body, expected):
    handler = media.JSONHandler(dumps=func)

    args = (body, b'application/javacript')

    if asgi:
        result = falcon.async_to_sync(handler.serialize_async, *args)
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
        s = BoundedStream(testing.ASGIRequestEventEmitter(body))
        args.insert(0, s)

        result = falcon.async_to_sync(handler.deserialize_async, *args)
    else:
        args.insert(0, io.BytesIO(body))
        result = handler.deserialize(*args)

    assert result == expected


@pytest.mark.parametrize('dumps, loads', ALL_JSON_IMPL, ids=ALL_JSON_IMPL_IDS)
@pytest.mark.parametrize('subclass', (True, False))
def test_full_app(asgi, util, dumps, loads, subclass):
    if subclass:

        class JSONHandlerSubclass(media.JSONHandler):
            pass

        handler = JSONHandlerSubclass(dumps=dumps, loads=loads)
        assert handler._serialize_sync is None
        assert handler._deserialize_sync is None
    else:
        handler = media.JSONHandler(dumps=dumps, loads=loads)
        assert handler._serialize_sync is not None
        assert handler._deserialize_sync is not None
    app = util.create_app(asgi)
    app.req_options.media_handlers[falcon.MEDIA_JSON] = handler
    app.resp_options.media_handlers[falcon.MEDIA_JSON] = handler

    if asgi:

        class Resp:
            async def on_get(self, req, res):
                res.media = await req.get_media()

    else:

        class Resp:
            def on_get(self, req, res):
                res.media = req.get_media()

    app.add_route('/go', Resp())

    data = {'foo': 123, 'bar': [2, 3], 'baz': {'x': 'y'}}
    res = testing.simulate_get(app, '/go', json=data)
    assert res.json == data


@pytest.mark.parametrize(
    'handler_mt',
    [
        'application/json',
        # NOTE(kgriffs): Include a bogus parameter to validate fuzzy matching logic
        'application/json; answer=42',
    ],
)
def test_deserialization_raises(asgi, util, handler_mt):
    app = util.create_app(asgi)

    class SuchException(Exception):
        pass

    class FaultyHandler(media.BaseHandler):
        def deserialize(self, stream, content_type, content_length):
            raise SuchException('Wow such error.')

        def deserialize_async(self, stream, content_type, content_length):
            raise SuchException('Wow such error.')

        def serialize(self, media, content_type):
            raise SuchException('Wow such error.')

    handlers = media.Handlers({handler_mt: FaultyHandler()})

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


def test_sync_methods_not_overridden(asgi, util):
    app = util.create_app(asgi)

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

    # NOTE(caselit): force serialization in xml,
    # since error.to_json uses the faulty handler
    result = testing.simulate_get(app, '/', headers={'Accept': 'text/xml'})
    assert result.status_code == 500

    result = testing.simulate_post(app, '/', json={}, headers={'Accept': 'text/xml'})
    assert result.status_code == 500


def test_async_methods_not_overridden(util):
    app = util.create_app(asgi=True)

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


def test_async_handler_returning_none(util):
    app = util.create_app(asgi=True)

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


def test_json_err_no_handler(asgi, util):
    app = util.create_app(asgi)

    handlers = media.Handlers({falcon.MEDIA_URLENCODED: media.URLEncodedFormHandler()})

    app.req_options.media_handlers = handlers
    app.resp_options.media_handlers = handlers

    class Resource:
        def on_get(self, req, resp):
            raise falcon.HTTPForbidden()

    app.add_route('/', Resource())

    result = testing.simulate_get(app, '/')
    assert result.status_code == 403
    assert result.json == falcon.HTTPForbidden().to_dict()


def test_handlers_include_new_media_handlers_in_resolving() -> None:
    handlers = media.Handlers({falcon.MEDIA_URLENCODED: media.URLEncodedFormHandler()})
    assert handlers._resolve(MEDIA_YAML, MEDIA_JSON, raise_not_found=False)[0] is None

    js_handler = media.JSONHandler()
    handlers[MEDIA_YAML] = js_handler
    resolved = handlers._resolve(MEDIA_YAML, MEDIA_JSON, raise_not_found=False)[0]
    assert resolved is js_handler


class TestBaseHandler:
    def test_defaultError(self):
        h = media.BaseHandler()

        def test(call):
            with pytest.raises(NotImplementedError) as e:
                call()

            assert e.value.args == ()

        test(lambda: h.serialize({}, 'my-type'))
        test(lambda: h.deserialize('', 'my-type', 0))

    def test_json(self):
        h = media.BaseHandler()

        with pytest.raises(
            NotImplementedError, match='The JSON media handler requires'
        ):
            h.serialize({}, falcon.MEDIA_JSON)
        with pytest.raises(
            NotImplementedError, match='The JSON media handler requires'
        ):
            h.deserialize('', falcon.MEDIA_JSON, 0)

        with pytest.raises(
            NotImplementedError, match='The JSON media handler requires'
        ):
            h.serialize({}, falcon.MEDIA_JSON + '; charset=UTF-8')
        with pytest.raises(
            NotImplementedError, match='The JSON media handler requires'
        ):
            h.deserialize('', falcon.MEDIA_JSON + '; charset=UTF-8', 0)
