import pytest

import falcon
from falcon import errors, media_handlers, testing


def create_client(handlers=None):
    res = testing.SimpleTestResource()

    app = falcon.API()
    app.add_route('/', res)

    if handlers:
        app.resp_options.media_handlers.update(handlers)

    client = testing.TestClient(app)
    client.resource = res

    return client


@pytest.mark.parametrize('media_type', [
    ('*/*'),
    ('application/json'),
    ('application/json; charset=utf-8'),
])
def test_json(media_type):
    client = create_client()
    client.simulate_get('/')

    resp = client.resource.captured_resp
    resp.content_type = media_type
    resp.media = {'something': True}

    assert resp.data == '{"something": true}'


@pytest.mark.parametrize('media_type', [
    ('application/msgpack'),
    ('application/msgpack; charset=utf-8'),
    ('application/x-msgpack'),
])
def test_msgpack(media_type):
    client = create_client({
        'application/msgpack': media_handlers.MessagePack,
        'application/x-msgpack': media_handlers.MessagePack,
    })
    client.simulate_get('/')

    resp = client.resource.captured_resp
    resp.content_type = media_type
    resp.media = {'something': True}

    assert resp.data == b'\x81\xa9something\xc3'


def test_unknown_media_type():
    client = create_client()
    client.simulate_get('/')

    resp = client.resource.captured_resp
    with pytest.raises(errors.HTTPUnsupportedMediaType) as err:
        resp.content_type = 'nope/json'
        resp.media = {'something': True}

    assert err.value.description == 'nope/json is a unsupported media type.'


def test_use_cached_media():
    expected = {'something': True}

    client = create_client()
    client.simulate_get('/')

    resp = client.resource.captured_resp
    resp._media = expected

    assert resp.media == expected


def test_default_media_type():
    client = create_client()
    client.simulate_get('/')

    resp = client.resource.captured_resp
    resp.content_type = ''
    resp.media = {'something': True}

    assert resp.data == '{"something": true}'
    assert resp.content_type == 'application/json; charset=UTF-8'
