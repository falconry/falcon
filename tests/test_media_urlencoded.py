import io

import pytest

import falcon
from falcon import media
from falcon import testing

from _util import create_app  # NOQA


def test_deserialize_empty_form():
    handler = media.URLEncodedFormHandler()
    stream = io.BytesIO(b'')
    assert handler.deserialize(stream, falcon.MEDIA_URLENCODED, 0) == {}


def test_deserialize_invalid_unicode():
    handler = media.URLEncodedFormHandler()
    stream = io.BytesIO('spade=♠'.encode())
    with pytest.raises(falcon.MediaMalformedError) as err:
        handler.deserialize(stream, falcon.MEDIA_URLENCODED, 9)
    assert isinstance(err.value.__cause__, UnicodeDecodeError)


@pytest.mark.parametrize(
    'data,expected',
    [
        ({'hello': 'world'}, b'hello=world'),
        ({'number': [1, 2]}, b'number=1&number=2'),
    ],
)
def test_urlencoded_form_handler_serialize(data, expected):
    handler = media.URLEncodedFormHandler()
    assert handler.serialize(data, falcon.MEDIA_URLENCODED) == expected

    value = falcon.async_to_sync(handler.serialize_async, data, falcon.MEDIA_URLENCODED)
    assert value == expected


class MediaMirror:
    def on_post(self, req, resp):
        resp.media = req.get_media()


class MediaMirrorAsync:
    async def on_post(self, req, resp):
        resp.media = await req.get_media()


@pytest.fixture
def client(asgi):
    app = create_app(asgi)
    app.add_route('/media', MediaMirrorAsync() if asgi else MediaMirror())
    return testing.TestClient(app)


def test_empty_form(client):
    resp = client.simulate_post(
        '/media', headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )

    assert resp.content == b'{}'


@pytest.mark.parametrize(
    'body,expected',
    [
        ('a=1&b=&c=3', {'a': '1', 'b': '', 'c': '3'}),
        ('param=undefined', {'param': 'undefined'}),
        ('color=green&color=black', {'color': ['green', 'black']}),
        (
            'food=hamburger+%28%F0%9F%8D%94%29&sauce=BBQ',
            {'food': 'hamburger (🍔)', 'sauce': 'BBQ'},
        ),
        ('flag%1&flag%2&flag%1&flag%2', {'flag%1': ['', ''], 'flag%2': ['', '']}),
    ],
)
def test_urlencoded_form(client, body, expected):
    resp = client.simulate_post(
        '/media',
        body=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    assert resp.json == expected
