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
    client.simulate_post('/', body=b'something', headers=headers)

    with pytest.raises(errors.HTTPUnsupportedMediaType) as err:
        client.resource.captured_req.media

    msg = '{} is an unsupported media type.'.format(media_type)
    assert err.value.description == msg


@pytest.mark.parametrize('media_type', [
    ('application/json'),
])
def test_exhausted_stream(media_type):
    client = create_client({
        'application/json': media.JSONHandler(),
    })
    headers = {'Content-Type': media_type}
    client.simulate_post('/', body='', headers=headers)

    assert client.resource.captured_req.media is None


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

    assert req.media is None


def test_use_cached_media():
    client = create_client()
    client.simulate_post('/')

    req = client.resource.captured_req
    req._media = {'something': True}

    assert req.media == {'something': True}


class NopeHandler(media.BaseHandler):

    def serialize(self, *args, **kwargs):
        pass

    def deserialize(self, *args, **kwargs):
        pass


def test_complete_consumption():
    client = create_client({
        'nope/nope': NopeHandler()
    })
    body = b'{"something": "abracadabra"}'
    headers = {'Content-Type': 'nope/nope'}

    client.simulate_post('/', body=body, headers=headers)

    req_media = client.resource.captured_req.media
    assert req_media is None
    req_bounded_stream = client.resource.captured_req.bounded_stream
    assert not req_bounded_stream.read()


@pytest.mark.parametrize('payload', [False, 0, 0.0, '', [], {}])
def test_empty_json_media(payload):
    client = create_client()
    client.simulate_post('/', json=payload)

    req = client.resource.captured_req
    for access in range(3):
        assert req.media == payload


def test_null_json_media():
    client = create_client()
    client.simulate_post('/', body='null',
                         headers={'Content-Type': 'application/json'})

    req = client.resource.captured_req
    for access in range(3):
        assert req.media is None
