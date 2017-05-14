import pytest

import falcon
from falcon import errors, media_handlers, testing


def create_client(handlers=None):
    res = testing.SimpleTestResource()

    app = falcon.API()
    app.add_route('/', res)

    if handlers:
        app.req_options.media_handlers.update(handlers)

    client = testing.TestClient(app)
    client.resource = res

    return client


@pytest.mark.parametrize('accept', [
    ('*/*'),
    ('application/json'),
    ('application/json; charset=utf-8'),
])
def test_json(accept):
    client = create_client()
    expected_body = b'{"something": true}'
    headers = {'Accept': accept}
    client.simulate_post('/', body=expected_body, headers=headers)

    media = client.resource.captured_req.media
    assert media is not None
    assert media.get('something') is True


@pytest.mark.parametrize('accept', [
    ('application/msgpack'),
    ('application/msgpack; charset=utf-8'),
    ('application/x-msgpack'),
])
def test_msgpack(accept):
    client = create_client({
        'application/msgpack': media_handlers.MessagePack,
        'application/x-msgpack': media_handlers.MessagePack,
    })
    expected_body = b'\x81\xa9something\xc3'
    headers = {'Accept': accept}
    client.simulate_post('/', body=expected_body, headers=headers)

    media = client.resource.captured_req.media
    assert media is not None
    assert media.get(b'something') is True


def test_unknown_media_type():
    client = create_client()
    headers = {'Accept': 'nope/json'}
    client.simulate_get('/', headers=headers)

    with pytest.raises(errors.HTTPUnsupportedMediaType) as err:
        client.resource.captured_req.media

    assert err.value.description == 'nope/json is a unsupported media type.'
