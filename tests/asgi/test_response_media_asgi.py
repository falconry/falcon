import json

import pytest

import falcon
from falcon import errors
from falcon import media
from falcon import testing
import falcon.asgi

try:
    import msgpack
except ImportError:
    msgpack = None


def create_client(resource, handlers=None):
    app = falcon.asgi.App()
    app.add_route('/', resource)

    if handlers:
        app.resp_options.media_handlers.update(handlers)

    client = testing.TestClient(app, headers={'capture-resp-media': 'yes'})

    return client


class SimpleMediaResource:
    def __init__(self, document, media_type=falcon.MEDIA_JSON):
        self._document = document
        self._media_type = media_type

    async def on_get(self, req, resp):
        resp.content_type = self._media_type
        resp.media = self._document
        resp.status = falcon.HTTP_OK


@pytest.mark.parametrize(
    'media_type',
    [
        ('*/*'),
        (falcon.MEDIA_JSON),
        ('application/json; charset=utf-8'),
    ],
)
def test_json(media_type):
    class TestResource:
        async def on_get(self, req, resp):
            resp.content_type = media_type
            resp.media = {'something': True}

            body = await resp.render_body()

            assert json.loads(body.decode('utf-8')) == {'something': True}

    client = create_client(TestResource())
    client.simulate_get('/')


@pytest.mark.parametrize(
    'document',
    [
        '',
        'I am a \u1d0a\ua731\u1d0f\u0274 string.',
        ['\u2665', '\u2660', '\u2666', '\u2663'],
        {'message': '\xa1Hello Unicode! \U0001f638'},
        {
            'description': 'A collection of primitive Python type examples.',
            'bool': False is not True and True is not False,
            'dict': {'example': 'mapping'},
            'float': 1.0,
            'int': 1337,
            'list': ['a', 'sequence', 'of', 'items'],
            'none': None,
            'str': 'ASCII string',
            'unicode': 'Hello Unicode! \U0001f638',
        },
    ],
)
def test_non_ascii_json_serialization(document):
    client = create_client(SimpleMediaResource(document))
    resp = client.simulate_get('/')
    assert resp.json == document


@pytest.mark.parametrize(
    'media_type',
    [
        (falcon.MEDIA_MSGPACK),
        ('application/msgpack; charset=utf-8'),
        ('application/x-msgpack'),
    ],
)
@pytest.mark.skipif(msgpack is None, reason='msgpack is required for this test')
def test_msgpack(media_type):
    class TestResource:
        async def on_get(self, req, resp):
            resp.content_type = media_type

            # Bytes
            resp.media = {b'something': True}
            assert (await resp.render_body()) == b'\x81\xc4\tsomething\xc3'

            # Unicode
            resp.media = {'something': True}
            body = await resp.render_body()
            assert body == b'\x81\xa9something\xc3'

            # Ensure that the result is being cached
            assert (await resp.render_body()) is body

    client = create_client(
        TestResource(),
        handlers={
            'application/msgpack': media.MessagePackHandler(),
            'application/x-msgpack': media.MessagePackHandler(),
        },
    )
    client.simulate_get('/')


def test_custom_media_handler():
    class PythonRepresentation(media.BaseHandler):
        async def serialize_async(media, content_type):
            return repr(media).encode()

    class TestResource:
        async def on_get(self, req, resp):
            resp.content_type = 'text/x-python-repr'
            resp.media = {'something': True}

            body = await resp.render_body()

            assert body == b"{'something': True}"

    client = create_client(
        TestResource(),
        handlers={
            'text/x-python-repr': PythonRepresentation(),
        },
    )
    client.simulate_get('/')


def test_unknown_media_type():
    class TestResource:
        async def on_get(self, req, resp):
            resp.content_type = 'nope/json'
            resp.media = {'something': True}

            try:
                await resp.render_body()
            except Exception as ex:
                # NOTE(kgriffs): pytest.raises triggers a failed test even
                #   when the correct error is raises, so we check it like
                #   this instead.
                assert isinstance(ex, errors.HTTPUnsupportedMediaType)
                raise

    client = create_client(TestResource())
    result = client.simulate_get('/')
    assert result.status_code == 415


def test_default_media_type():
    doc = {'something': True}

    class TestResource:
        async def on_get(self, req, resp):
            resp.content_type = ''
            resp.media = {'something': True}

            body = await resp.render_body()
            assert json.loads(body.decode('utf-8')) == doc
            assert resp.content_type == 'application/json'

    client = create_client(TestResource())
    result = client.simulate_get('/')
    assert result.json == doc


def test_mimeparse_edgecases():
    doc = {'something': True}

    class TestResource:
        async def on_get(self, req, resp):
            resp.content_type = 'application/vnd.something'
            with pytest.raises(errors.HTTPUnsupportedMediaType):
                resp.media = {'something': False}
                await resp.render_body()

            resp.content_type = 'invalid'
            with pytest.raises(errors.HTTPUnsupportedMediaType):
                resp.media = {'something': False}
                await resp.render_body()

            # Shouldn't raise
            for content_type in (None, '*/*'):
                resp.content_type = content_type
                resp.media = doc

    client = create_client(TestResource())

    result = client.simulate_get('/')
    assert result.json == doc


def run_test(test_fn):
    doc = {'something': True}

    class TestResource:
        async def on_get(self, req, resp):
            await test_fn(resp)

            resp.text = None
            resp.data = None
            resp.media = doc

    client = create_client(TestResource())
    result = client.simulate_get('/')
    assert result.json == doc


class TestRenderBodyPrecedence:
    def test_text(self):
        async def test(resp):
            resp.text = 'body'
            resp.data = b'data'
            resp.media = ['media']

            assert await resp.render_body() == b'body'

        run_test(test)

    def test_data(self):
        async def test(resp):
            resp.data = b'data'
            resp.media = ['media']

            assert await resp.render_body() == b'data'

        run_test(test)

    def test_data_masquerading_as_text(self):
        async def test(resp):
            resp.text = b'data'
            resp.media = ['media']

            assert await resp.render_body() == b'data'

        run_test(test)

    def test_media(self):
        async def test(resp):
            resp.media = ['media']
            assert json.loads((await resp.render_body()).decode('utf-8')) == ['media']

        run_test(test)


def test_media_rendered_cached():
    async def test(resp):
        resp.media = {'foo': 'bar'}

        first = await resp.render_body()
        assert first is await resp.render_body()
        assert first is resp._media_rendered

        resp.media = 123
        assert first is not await resp.render_body()

    run_test(test)


def test_custom_render_body():
    class CustomResponse(falcon.asgi.Response):
        async def render_body(self):
            body = await super().render_body()

            if not self.content_type.startswith('text/plain'):
                return body

            if not body.endswith(b'\n'):
                # Be a good Unix netizen
                return body + b'\n'

            return body

    class HelloResource:
        async def on_get(self, req, resp):
            resp.content_type = falcon.MEDIA_TEXT
            resp.text = 'Hello, World!'

    app = falcon.asgi.App(response_type=CustomResponse)
    app.add_route('/', HelloResource())

    resp = testing.simulate_get(app, '/')
    assert resp.headers['Content-Type'] == 'text/plain; charset=utf-8'
    assert resp.text == 'Hello, World!\n'
