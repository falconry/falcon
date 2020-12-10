import pytest

from falcon import errors, media, testing

from _util import create_app  # NOQA


def create_client(asgi, handlers=None, resource=None):
    if not resource:
        resource = testing.SimpleTestResourceAsync() if asgi else testing.SimpleTestResource()

    app = create_app(asgi)
    app.add_route('/', resource)

    if handlers:
        app.req_options.media_handlers.update(handlers)

    client = testing.TestClient(app, headers={'capture-req-media': 'yes'})
    client.resource = resource

    return client


@pytest.fixture(params=[True, False])
def client(request):
    return create_client(request.param)


class ResourceCachedMedia:
    def on_post(self, req, resp, **kwargs):
        self.captured_req_media = req.media

        # NOTE(kgriffs): Ensure that the media object is cached
        assert self.captured_req_media is req.get_media()


class ResourceCachedMediaAsync:
    async def on_post(self, req, resp, **kwargs):
        self.captured_req_media = await req.get_media()

        # NOTE(kgriffs): Ensure that the media object is cached
        assert self.captured_req_media is await req.get_media()


class ResourceInvalidMedia:
    def __init__(self, expected_error):
        self._expected_error = expected_error

    def on_post(self, req, resp, **kwargs):
        with pytest.raises(self._expected_error) as error:
            req.media

        self.captured_error = error


class ResourceInvalidMediaAsync:
    def __init__(self, expected_error):
        self._expected_error = expected_error

    async def on_post(self, req, resp, **kwargs):
        with pytest.raises(self._expected_error) as error:
            await req.get_media()

        self.captured_error = error


@pytest.mark.parametrize('media_type', [
    (None),
    ('*/*'),
    ('application/json'),
    ('application/json; charset=utf-8'),
])
def test_json(client, media_type):
    expected_body = b'{"something": true}'
    headers = {'Content-Type': media_type}
    client.simulate_post('/', body=expected_body, headers=headers)

    media = client.resource.captured_req_media
    assert media is not None
    assert media.get('something') is True


@pytest.mark.parametrize('media_type', [
    ('application/msgpack'),
    ('application/msgpack; charset=utf-8'),
    ('application/x-msgpack'),
])
def test_msgpack(asgi, media_type):
    client = create_client(asgi, {
        'application/msgpack': media.MessagePackHandler(),
        'application/x-msgpack': media.MessagePackHandler(),
    })
    headers = {'Content-Type': media_type}

    # Bytes
    expected_body = b'\x81\xc4\tsomething\xc3'
    client.simulate_post('/', body=expected_body, headers=headers)

    req_media = client.resource.captured_req_media
    assert req_media.get(b'something') is True

    # Unicode
    expected_body = b'\x81\xa9something\xc3'
    client.simulate_post('/', body=expected_body, headers=headers)

    req_media = client.resource.captured_req_media
    assert req_media.get('something') is True


@pytest.mark.parametrize('media_type', [
    ('nope/json'),
])
def test_unknown_media_type(asgi, media_type):
    client = _create_client_invalid_media(asgi, errors.HTTPUnsupportedMediaType)

    headers = {'Content-Type': media_type}
    client.simulate_post('/', body=b'something', headers=headers)

    title_msg = '415 Unsupported Media Type'
    description_msg = '{} is an unsupported media type.'.format(media_type)
    assert client.resource.captured_error.value.title == title_msg
    assert client.resource.captured_error.value.description == description_msg


@pytest.mark.parametrize('media_type', [
    ('application/json'),
])
def test_exhausted_stream(asgi, media_type):
    client = create_client(asgi, {
        'application/json': media.JSONHandler(),
    })
    headers = {'Content-Type': media_type}
    client.simulate_post('/', body='', headers=headers)

    assert client.resource.captured_req_media is None


def test_invalid_json(asgi):
    client = _create_client_invalid_media(asgi, errors.HTTPBadRequest)

    expected_body = b'{'
    headers = {'Content-Type': 'application/json'}
    client.simulate_post('/', body=expected_body, headers=headers)

    assert 'Could not parse JSON body' in client.resource.captured_error.value.description


def test_invalid_msgpack(asgi):
    handlers = {
        'application/msgpack': media.MessagePackHandler()
    }
    client = _create_client_invalid_media(asgi, errors.HTTPBadRequest, handlers=handlers)

    expected_body = '/////////////////////'
    headers = {'Content-Type': 'application/msgpack'}
    client.simulate_post('/', body=expected_body, headers=headers)

    desc = 'Could not parse MessagePack body - unpack(b) received extra data.'
    assert client.resource.captured_error.value.description == desc


def test_invalid_stream_fails_gracefully(client):
    client.simulate_post('/')

    req = client.resource.captured_req
    req.headers['Content-Type'] = 'application/json'
    req._bounded_stream = None

    assert client.resource.captured_req_media is None


class NopeHandler(media.BaseHandler):

    def serialize(self, *args, **kwargs):
        pass

    def deserialize(self, *args, **kwargs):
        pass

    exhaust_stream = True


def test_complete_consumption(asgi):
    client = create_client(asgi, {
        'nope/nope': NopeHandler()
    })
    body = b'{"something": "abracadabra"}'
    headers = {'Content-Type': 'nope/nope'}

    client.simulate_post('/', body=body, headers=headers)

    req_media = client.resource.captured_req_media
    assert req_media is None
    req_bounded_stream = client.resource.captured_req.bounded_stream
    assert req_bounded_stream.eof


@pytest.mark.parametrize('payload', [False, 0, 0.0, '', [], {}])
def test_empty_json_media(asgi, payload):
    resource = ResourceCachedMediaAsync() if asgi else ResourceCachedMedia()
    client = create_client(asgi, resource=resource)
    client.simulate_post('/', json=payload)
    assert resource.captured_req_media == payload


def test_null_json_media(client):
    client.simulate_post('/', body='null',
                         headers={'Content-Type': 'application/json'})
    assert client.resource.captured_req_media is None


def _create_client_invalid_media(asgi, error_type, handlers=None):
    resource_type = ResourceInvalidMediaAsync if asgi else ResourceInvalidMedia
    resource = resource_type(error_type)
    return create_client(asgi, handlers=handlers, resource=resource)
