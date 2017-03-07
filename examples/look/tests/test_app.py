import io
from unittest.mock import call, MagicMock, mock_open

import look.app
import look.images

import msgpack
import pytest

import falcon
from falcon import testing
import falcon.request_helpers


@pytest.fixture
def mock_saver():
    return MagicMock()


@pytest.fixture
def client(mock_saver):
    api = look.app.create_app(mock_saver)
    return testing.TestClient(api)


def test_get_message(client):
    doc = {u'message': u'Hello world!'}

    response = client.simulate_get('/images')
    result_doc = msgpack.unpackb(response.content, encoding='utf-8')

    assert result_doc == doc
    assert response.status == falcon.HTTP_OK


# With clever composition of fixtures, we can observe what happens with
# the mock injected into the image resource.
def test_post_image(client, mock_saver):
    file_name = 'fake-image-name.xyz'
    # we need to know what ImageSaver method will be used
    mock_saver.save.return_value = file_name
    image_content_type = 'image/xyz'

    response = client.simulate_post('/images',
                                    body=b'some-fake-bytes',
                                    headers={'content-type': image_content_type})

    assert response.status == falcon.HTTP_CREATED
    assert response.headers['location'] == '/images/{}'.format(file_name)
    saver_call = mock_saver.save.call_args
    # saver_call is a unittest.mock.call tuple.
    # It's first element is a tuple of positional arguments supplied when calling the mock.
    assert isinstance(saver_call[0][0], falcon.request_helpers.BoundedStream)
    assert saver_call[0][1] == image_content_type


def test_saving_image(monkeypatch):
    # this still has some mocks, but they are more localized
    mock_file_open = mock_open()
    monkeypatch.setattr('builtins.open', mock_file_open)
    fake_uuid = 'blablabla'
    monkeypatch.setattr('look.images.uuid.uuid4', lambda: fake_uuid)

    fake_image_bytes = b'fake-image-bytes'
    fake_request_stream = io.BytesIO(fake_image_bytes)
    storage_path = 'fake-storage-path'
    saver = look.images.ImageSaver(storage_path)

    assert saver.save(fake_request_stream, 'image/png') == fake_uuid + '.png'
    assert call().write(fake_image_bytes) in mock_file_open.mock_calls
