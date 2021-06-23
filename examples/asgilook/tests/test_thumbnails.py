def test_missing_in_store(client):
    resp = client.simulate_get(
        '/thumbnails/1a256a8a-2063-46ff-b53f-d04d5bcf5eee/80x80.jpeg'
    )
    assert resp.status_code == 404


def test_thumbnails(client, png_image, image_size):
    resp1 = client.simulate_post('/images', body=png_image)
    assert resp1.status_code == 201

    thumbnails = resp1.json['thumbnails']
    assert set(thumbnails) == {
        '/thumbnails/36562622-48e5-4a61-be67-e426b11821ed/320x180.jpeg',
        '/thumbnails/36562622-48e5-4a61-be67-e426b11821ed/160x90.jpeg',
    }

    for uri in thumbnails:
        resp = client.simulate_get(uri)
        assert resp.headers['Content-Type'] == 'image/jpeg'
        assert resp.headers['X-ASGILook-Cache'] == 'Miss'
        assert image_size(resp.content) in ((320, 180), (160, 90))


def test_missing_size(client, png_image):
    client.simulate_post('/images', body=png_image)

    resp = client.simulate_get(
        '/thumbnails/36562622-48e5-4a61-be67-e426b11821ed/480x270.jpeg'
    )
    assert resp.status_code == 404


def test_thumbnail_caching(client, png_image):
    client.simulate_post('/images', body=png_image)

    reference = None
    for retry in range(4):
        resp = client.simulate_get(
            '/thumbnails/36562622-48e5-4a61-be67-e426b11821ed/160x90.jpeg'
        )
        assert resp.status_code == 200
        if retry == 0:
            assert resp.headers.get('X-ASGILook-Cache') == 'Miss'
            reference = resp.content
        else:
            assert resp.headers.get('X-ASGILook-Cache') == 'Hit'
            assert resp.content == reference
