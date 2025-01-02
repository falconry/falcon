import io
import os
from unittest import TestCase
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import mock_open
import uuid
from wsgiref.validate import InputWrapper

import pytest

import falcon
from falcon import testing

import look.app
import look.images


@pytest.fixture
def mock_store():
    return MagicMock()


@pytest.fixture
def client(mock_store):
    api = look.app.create_app(mock_store)
    return testing.TestClient(api)


def test_list_images(client, mock_store):
    images = ['first-file', 'second-file', 'third-file']
    image_docs = [{'href': '/images/' + image} for image in images]

    mock_store.list.return_value = images

    response = client.simulate_get('/images')

    result = response.json

    assert result['images'] == image_docs
    assert response.status == falcon.HTTP_OK


# With clever composition of fixtures, we can observe what happens with
# the mock injected into the image resource.
def test_post_image(client, mock_store):
    file_name = 'fake-image-name.xyz'

    # We need to know what ImageStore method will be used
    mock_store.save.return_value = file_name
    image_content_type = 'image/xyz'

    response = client.simulate_post(
        '/images', body=b'some-fake-bytes', headers={'content-type': image_content_type}
    )

    assert response.status == falcon.HTTP_CREATED
    assert response.headers['location'] == '/images/{}'.format(file_name)
    saver_call = mock_store.save.call_args

    # saver_call is a unittest.mock.call tuple. It's first element is a
    # tuple of positional arguments supplied when calling the mock.
    assert isinstance(saver_call[0][0], InputWrapper)
    assert saver_call[0][1] == image_content_type


def test_saving_image():
    # This still has some mocks, but they are more localized and do not
    # have to be monkey-patched into standard library modules (always a
    # risky business).
    mock_file_open = mock_open()

    fake_uuid = '123e4567-e89b-12d3-a456-426655440000'

    def mock_uuidgen():
        return fake_uuid

    fake_image_bytes = b'fake-image-bytes'
    fake_request_stream = io.BytesIO(fake_image_bytes)
    storage_path = 'fake-storage-path'
    store = look.images.ImageStore(
        storage_path, uuidgen=mock_uuidgen, fopen=mock_file_open
    )

    assert store.save(fake_request_stream, 'image/png') == fake_uuid + '.png'
    assert call().write(fake_image_bytes) in mock_file_open.mock_calls


def test_get_image(client, mock_store):
    file_bytes = b'fake-image-bytes'

    mock_store.open.return_value = ((file_bytes,), 17)

    response = client.simulate_get('/images/filename.png')

    assert response.status == falcon.HTTP_OK
    assert response.content == file_bytes


def test_opening_image():
    file_name = f'{uuid.uuid4()}.png'
    storage_path = '.'
    file_path = f'{storage_path}/{file_name}'
    fake_image_bytes = b'fake-image-bytes'
    with open(file_path, 'wb') as image_file:
        file_length = image_file.write(fake_image_bytes)

    store = look.images.ImageStore(storage_path)

    file_reader, content_length = store.open(file_name)
    assert content_length == file_length
    assert file_reader.read() == fake_image_bytes
    os.remove(file_path)

    with TestCase().assertRaises(IOError):
        store.open('wrong_file_name_format')


def test_listing_images():
    file_names = [f'{uuid.uuid4()}.png' for _ in range(2)]
    storage_path = '.'
    file_paths = [f'{storage_path}/{name}' for name in file_names]
    fake_images_bytes = [
        b'fake-image-bytes',  # 17
        b'fake-image-bytes-with-more-length',  # 34
    ]
    for i in range(2):
        with open(file_paths[i], 'wb') as image_file:
            image_file.write(fake_images_bytes[i])

    store = look.images.ImageStore(storage_path)
    assert store.list(10) == []
    assert store.list(20) == [file_names[0]]
    assert len(store.list(40)) == 2
    assert sorted(store.list(40)) == sorted(file_names)

    for file_path in file_paths:
        os.remove(file_path)
