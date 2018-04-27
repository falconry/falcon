import pytest

import falcon
from falcon import errors, media, testing


def create_client(handlers=None):
    res = testing.SimpleTestResource()

    app = falcon.API()
    app.add_route('/', res)

    if handlers:
        app.req_options.media_handlers.update(handlers)

    client = testing.TestClient(app)
    client.resource = res

    return client


@pytest.mark.parametrize('media_type', [
    (None),
    ('*/*'),
    ('application/json'),
    ('application/json; charset=utf-8'),
])
def test_json(media_type):
    client = create_client()
    expected_body = b'{"something": true}'
    headers = {'Content-Type': media_type}
    client.simulate_post('/', body=expected_body, headers=headers)

    media = client.resource.captured_req.media
    assert media is not None
    assert media.get('something') is True


@pytest.mark.parametrize('media_type', [
    ('application/msgpack'),
    ('application/msgpack; charset=utf-8'),
    ('application/x-msgpack'),
])
def test_msgpack(media_type):
    client = create_client({
        'application/msgpack': media.MessagePackHandler(),
        'application/x-msgpack': media.MessagePackHandler(),
    })
    headers = {'Content-Type': media_type}

    # Bytes
    expected_body = b'\x81\xc4\tsomething\xc3'
    client.simulate_post('/', body=expected_body, headers=headers)

    req_media = client.resource.captured_req.media
    assert req_media.get(b'something') is True

    # Unicode
    expected_body = b'\x81\xa9something\xc3'
    client.simulate_post('/', body=expected_body, headers=headers)

    req_media = client.resource.captured_req.media
    assert req_media.get(u'something') is True


@pytest.mark.parametrize('media_type', [
    ('nope/json'),
])
def test_unknown_media_type(media_type):
    client = create_client()
    headers = {'Content-Type': media_type}
    client.simulate_post('/', body='', headers=headers)

    with pytest.raises(errors.HTTPUnsupportedMediaType) as err:
        client.resource.captured_req.media

    msg = '{} is an unsupported media type.'.format(media_type)
    assert err.value.description == msg


def test_invalid_json():
    client = create_client()
    expected_body = b'{'
    headers = {'Content-Type': 'application/json'}
    client.simulate_post('/', body=expected_body, headers=headers)

    with pytest.raises(errors.HTTPBadRequest) as err:
        client.resource.captured_req.media

    assert 'Could not parse JSON body' in err.value.description


def test_invalid_msgpack():
    client = create_client({'application/msgpack': media.MessagePackHandler()})
    expected_body = '/////////////////////'
    headers = {'Content-Type': 'application/msgpack'}
    client.simulate_post('/', body=expected_body, headers=headers)

    with pytest.raises(errors.HTTPBadRequest) as err:
        client.resource.captured_req.media

    desc = 'Could not parse MessagePack body - unpack(b) received extra data.'
    assert err.value.description == desc


def test_invalid_stream_fails_gracefully():
    client = create_client()
    client.simulate_post('/')

    req = client.resource.captured_req
    req.headers['Content-Type'] = 'application/json'
    req._bounded_stream = None

    with pytest.raises(errors.HTTPBadRequest) as err:
        req.media

    assert 'Could not parse JSON body' in err.value.description


def test_use_cached_media():
    client = create_client()
    client.simulate_post('/')

    req = client.resource.captured_req
    req._media = {'something': True}

    assert req.media == {'something': True}
