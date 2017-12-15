import json

import pytest

import falcon
from falcon import errors, media, testing


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
    (falcon.MEDIA_JSON),
    ('application/json; charset=utf-8'),
])
def test_json(media_type):
    client = create_client()
    client.simulate_get('/')

    resp = client.resource.captured_resp
    resp.content_type = media_type
    resp.media = {'something': True}

    assert json.loads(resp.data.decode('utf-8')) == {u'something': True}


@pytest.mark.parametrize('media_type', [
    (falcon.MEDIA_MSGPACK),
    ('application/msgpack; charset=utf-8'),
    ('application/x-msgpack'),
])
def test_msgpack(media_type):
    client = create_client({
        'application/msgpack': media.MessagePackHandler(),
        'application/x-msgpack': media.MessagePackHandler(),
    })
    client.simulate_get('/')

    resp = client.resource.captured_resp
    resp.content_type = media_type

    # Bytes
    resp.media = {b'something': True}
    assert resp.data == b'\x81\xc4\tsomething\xc3'

    # Unicode
    resp.media = {u'something': True}
    assert resp.data == b'\x81\xa9something\xc3'


def test_unknown_media_type():
    client = create_client()
    client.simulate_get('/')

    resp = client.resource.captured_resp
    with pytest.raises(errors.HTTPUnsupportedMediaType) as err:
        resp.content_type = 'nope/json'
        resp.media = {'something': True}

    assert err.value.description == 'nope/json is an unsupported media type.'


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

    assert json.loads(resp.data.decode('utf-8')) == {u'something': True}
    assert resp.content_type == 'application/json; charset=UTF-8'


def test_mimeparse_edgecases():
    client = create_client()
    client.simulate_get('/')

    resp = client.resource.captured_resp

    resp.content_type = 'application/vnd.something'
    with pytest.raises(errors.HTTPUnsupportedMediaType):
        resp.media = {'something': True}

    resp.content_type = 'invalid'
    with pytest.raises(errors.HTTPUnsupportedMediaType):
        resp.media = {'something': True}

    # Clear the content type, shouldn't raise this time
    resp.content_type = None
    resp.media = {'something': True}
