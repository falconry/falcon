import os

import requests


def test_posted_image_gets_saved():
    file_save_prefix = '/tmp/'
    location_prefix = '/images/'
    fake_image_bytes = b'fake-image-bytes'

    response = requests.post(
        'http://localhost:8000/images',
        data=fake_image_bytes,
        headers={'content-type': 'image/png'}
    )

    assert response.status_code == 201
    location = response.headers['location']
    assert location.startswith(location_prefix)
    image_name = location.replace(location_prefix, '')

    file_path = file_save_prefix + image_name
    with open(file_path, 'rb') as image_file:
        assert image_file.read() == fake_image_bytes

    os.remove(file_path)
