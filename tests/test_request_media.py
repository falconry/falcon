import pytest

import falcon
from falcon import errors, media, testing


@pytest.fixture
def builder_client():
    resource = testing.SimpleTestResource()
    app = falcon.APIBuilder() \
        .add_get_route('/', resource.on_get) \
        .add_post_route('/', resource.on_post) \
        .build()
    client = testing.TestClient(app)
    client.resource = resource
    return client


@pytest.fixture
def client():
    res = testing.SimpleTestResource()
    app = falcon.API()
    app.add_route('/', res)
    client = testing.TestClient(app)
    client.resource = res
    return client


@pytest.mark.parametrize('media_type', [
    (None),
    ('*/*'),
    ('application/json'),
    ('application/json; charset=utf-8'),
])
@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_json(media_type, client):
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
@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_msgpack(media_type, client):
    client.app.req_options.media_handlers.update({
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
@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_unknown_media_type(media_type, client):
    headers = {'Content-Type': media_type}
    client.simulate_post('/', body=b'something', headers=headers)

    with pytest.raises(errors.HTTPUnsupportedMediaType) as err:
        client.resource.captured_req.media

    msg = '{} is an unsupported media type.'.format(media_type)
    assert err.value.description == msg


@pytest.mark.parametrize('media_type', [
    ('application/json'),
])
@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_exhausted_stream(media_type, client):
    client.app.req_options.media_handlers.update({
        'application/json': media.JSONHandler(),
    })
    headers = {'Content-Type': media_type}
    client.simulate_post('/', body='', headers=headers)

    assert client.resource.captured_req.media is None


@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_invalid_json(client):
    expected_body = b'{'
    headers = {'Content-Type': 'application/json'}
    client.simulate_post('/', body=expected_body, headers=headers)

    with pytest.raises(errors.HTTPBadRequest) as err:
        client.resource.captured_req.media

    assert 'Could not parse JSON body' in err.value.description


@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_invalid_msgpack(client):
    client.app.req_options.media_handlers.update({
        'application/msgpack': media.MessagePackHandler()
    })
    expected_body = '/////////////////////'
    headers = {'Content-Type': 'application/msgpack'}
    client.simulate_post('/', body=expected_body, headers=headers)

    with pytest.raises(errors.HTTPBadRequest) as err:
        client.resource.captured_req.media

    desc = 'Could not parse MessagePack body - unpack(b) received extra data.'
    assert err.value.description == desc


@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_invalid_stream_fails_gracefully(client):
    client.simulate_post('/')

    req = client.resource.captured_req
    req.headers['Content-Type'] = 'application/json'
    req._bounded_stream = None

    assert req.media is None


@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_use_cached_media(client):
    client.simulate_post('/')

    req = client.resource.captured_req
    req._media = {'something': True}

    assert req.media == {'something': True}


class NopeHandler(media.BaseHandler):

    def serialize(self, *args, **kwargs):
        pass

    def deserialize(self, *args, **kwargs):
        pass


@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_complete_consumption(client):
    client.app.req_options.media_handlers.update({
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
@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_empty_json_media(payload, client):
    client.simulate_post('/', json=payload)

    req = client.resource.captured_req
    for access in range(3):
        assert req.media == payload


@pytest.mark.parametrize('client', [
    'client',
    'builder_client'
], indirect=True)
def test_null_json_media(client):
    client.simulate_post('/', body='null',
                         headers={'Content-Type': 'application/json'})

    req = client.resource.captured_req
    for access in range(3):
        assert req.media is None
