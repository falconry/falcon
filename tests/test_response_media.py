import json

import pytest

import falcon
from falcon import errors, media, testing
from falcon.util.deprecation import DeprecatedWarning


@pytest.fixture
def client():
    return create_client()


def create_client(handlers=None):
    res = testing.SimpleTestResource()

    app = falcon.App()
    app.add_route('/', res)

    if handlers:
        app.resp_options.media_handlers.update(handlers)

    client = testing.TestClient(app)
    client.resource = res

    return client


class SimpleMediaResource:
    def __init__(self, document, media_type=falcon.MEDIA_JSON):
        self._document = document
        self._media_type = media_type

    def on_get(self, req, resp):
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
def test_json(client, media_type):
    client.simulate_get('/')

    resp = client.resource.captured_resp
    resp.content_type = media_type
    resp.media = {'something': True}

    assert json.loads(resp.render_body().decode('utf-8')) == {'something': True}


@pytest.mark.parametrize(
    'document',
    [
        '',
        'I am a \u1d0a\ua731\u1d0f\u0274 string.',
        ['\u2665', '\u2660', '\u2666', '\u2663'],
        {'message': '\xa1Hello Unicode! \U0001F638'},
        {
            'description': 'A collection of primitive Python type examples.',
            'bool': False is not True and True is not False,
            'dict': {'example': 'mapping'},
            'float': 1.0,
            'int': 1337,
            'list': ['a', 'sequence', 'of', 'items'],
            'none': None,
            'str': 'ASCII string',
            'unicode': 'Hello Unicode! \U0001F638',
        },
    ],
)
def test_non_ascii_json_serialization(document):
    app = falcon.App()
    app.add_route('/', SimpleMediaResource(document))
    client = testing.TestClient(app)

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
def test_msgpack(media_type):
    client = create_client(
        {
            'application/msgpack': media.MessagePackHandler(),
            'application/x-msgpack': media.MessagePackHandler(),
        }
    )
    client.simulate_get('/')

    resp = client.resource.captured_resp
    resp.content_type = media_type

    # Bytes
    resp.media = {b'something': True}
    assert resp.render_body() == b'\x81\xc4\tsomething\xc3'

    # Unicode
    resp.media = {'something': True}
    assert resp.render_body() == b'\x81\xa9something\xc3'


def test_unknown_media_type(client):
    client.simulate_get('/')

    resp = client.resource.captured_resp
    with pytest.raises(errors.HTTPUnsupportedMediaType) as err:
        resp.content_type = 'nope/json'
        resp.media = {'something': True}
        resp.render_body()

    assert err.value.description == 'nope/json is an unsupported media type.'


def test_use_cached_media(client):
    client.simulate_get('/')

    resp = client.resource.captured_resp

    expected = {'something': True}
    resp._media = expected
    assert resp.media == expected


def test_default_media_type(client):
    client.simulate_get('/')

    resp = client.resource.captured_resp
    resp.content_type = ''
    resp.media = {'something': True}

    assert json.loads(resp.render_body().decode('utf-8')) == {'something': True}
    assert resp.content_type == 'application/json'


def test_mimeparse_edgecases(client):
    client.simulate_get('/')

    resp = client.resource.captured_resp

    resp.content_type = 'application/vnd.something'
    with pytest.raises(errors.HTTPUnsupportedMediaType):
        resp.media = {'something': True}
        resp.render_body()

    resp.content_type = 'invalid'
    with pytest.raises(errors.HTTPUnsupportedMediaType):
        resp.media = {'something': True}
        resp.render_body()

    # Clear the content type, shouldn't raise this time
    resp.content_type = None
    resp.media = {'something': True}


class TestRenderBodyPrecedence:
    def test_text(self, client):
        client.simulate_get('/')

        resp = client.resource.captured_resp

        resp.text = 'body'
        resp.data = b'data'
        resp.media = ['media']

        assert resp.render_body() == b'body'

    def test_body(self, client):
        client.simulate_get('/')

        resp = client.resource.captured_resp
        with pytest.warns(DeprecatedWarning, match='Please use text instead'):
            resp.body = 'body'
        resp.data = b'data'
        resp.media = ['media']

        assert resp.render_body() == b'body'

    def test_data(self, client):
        client.simulate_get('/')

        resp = client.resource.captured_resp

        resp.data = b'data'
        resp.media = ['media']

        assert resp.render_body() == b'data'

    def test_media(self, client):
        client.simulate_get('/')

        resp = client.resource.captured_resp
        resp.media = ['media']

        assert json.loads(resp.render_body().decode('utf-8')) == ['media']


def test_media_rendered_cached(client):
    client.simulate_get('/')

    resp = client.resource.captured_resp

    resp.media = {'foo': 'bar'}

    first = resp.render_body()
    assert first is resp.render_body()
    assert first is resp._media_rendered

    resp.media = 123
    assert first is not resp.render_body()
