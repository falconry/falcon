import io

import pytest

import falcon
from falcon import media
from falcon import testing


def test_deserialize_empty_form():
    handler = media.URLEncodedFormHandler()
    stream = io.BytesIO(b'')
    assert handler.deserialize(stream, falcon.MEDIA_URLENCODED, 0) is None


def test_deserialize_invalid_unicode():
    handler = media.URLEncodedFormHandler()
    stream = io.BytesIO('spade=♠'.encode())
    with pytest.raises(UnicodeDecodeError):
        print(handler.deserialize(stream, falcon.MEDIA_URLENCODED, 9))


@pytest.mark.parametrize('data,expected', [
    ({'hello': 'world'}, 'hello=world'),
    ({'number': [1, 2]}, 'number=1&number=2'),
])
def test_urlencoded_form_handler_serialize(data, expected):
    handler = media.URLEncodedFormHandler()
    assert handler.serialize(data, falcon.MEDIA_URLENCODED) == expected


class MediaMirror:

    @classmethod
    def on_post(cls, req, resp):
        resp.media = req.media


@pytest.fixture
def client():
    handlers = media.Handlers({
        'application/json': media.JSONHandler(),
        'application/x-www-form-urlencoded': media.URLEncodedFormHandler(),
    })
    api = falcon.API()
    api.req_options.media_handlers = handlers
    api.resp_options.media_handlers = handlers

    api.add_route('/media', MediaMirror())

    return testing.TestClient(api)


def test_empty_form(client):
    resp = client.simulate_post(
        '/media',
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    assert resp.content == b''


@pytest.mark.parametrize('body,expected', [
    ('a=1&b=&c=3', {'a': '1', 'b': '', 'c': '3'}),
    ('param=undefined', {'param': 'undefined'}),
    ('color=green&color=black', {'color': ['green', 'black']}),
])
def test_urlencoded_form(client, body, expected):
    resp = client.simulate_post(
        '/media',
        body=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    assert resp.json == expected
