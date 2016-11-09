import requests


def test_posted_image_gets_saved():
    location_prefix = '/images/'
    fake_image_bytes = b'fake-image-bytes'

    response = requests.post('http://localhost:8000/images',
                             data=fake_image_bytes,
                             headers={'content-type': 'image/png'})

    assert response.status_code == 201
    location = response.headers['location']
    assert location.startswith(location_prefix)
    filename = location.replace(location_prefix, '')
    # assuming that the storage path is "/tmp"
    with open('/tmp/' + filename, 'rb') as image_file:
        assert image_file.read() == fake_image_bytes
